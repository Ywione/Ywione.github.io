"""Check the local QBS folder or prepare a validated release in an isolated directory."""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo
from qbs_source import SourceError, digest, latest_published, select_source

SITE = Path(__file__).resolve().parents[2]


def run(command, **kwargs):
    subprocess.run([str(x) for x in command], check=True, **kwargs)


def extract_source(site, config, source, target):
    env = os.environ.copy()
    env['PYTHONPATH'] = str(site / '.qbs-local/python') + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    python = Path(config['runtime_directory']).expanduser() / 'python/bin/python3'
    run([python, site / 'scripts/qds/extract_qds.py', source, target], env=env, stdout=subprocess.DEVNULL)


def inspect_release(site, config):
    source, period = select_source(config['source_directory'])
    published_period, published = latest_published(site)
    sha = digest(source)
    if published_period and period < published_period:
        raise SourceError('The source folder only contains older QBS editions than the website. No downgrade will be made.')
    status = 'unchanged' if published_period == period and published['sourceSha256'] == sha else 'available'
    if status == 'available' and published_period == period and published.get('dataSha256'):
        with tempfile.TemporaryDirectory(prefix='qbs-content-') as temporary:
            target = Path(temporary) / 'source.json'
            extract_source(site, config, source, target)
            extracted = json.loads(target.read_text())
            if digest(source) != sha:
                raise SourceError('QBS changed during inspection. Retry after the save finishes.')
            if extracted['dataSha256'] == published['dataSha256']:
                status = 'unchanged'
    return {'status': status, 'source': str(source), 'source_sha256': sha,
            'edition': f'{period[0]}-q{period[1]}', 'previous_edition': published.get('edition') if published else None}


def prepare(site, config, release):
    if release['status'] == 'unchanged':
        return release
    # Preserve all previous editions; never run generation against the live checkout.
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=site).strip():
        raise SourceError('Website checkout has uncommitted changes. Reconcile them before preparing a QBS release.')
    work = site / '.qbs-local'
    work.mkdir(exist_ok=True)
    job = Path(tempfile.mkdtemp(prefix='release-', dir=work))
    stage, review = job / 'site', job / 'review'
    review.mkdir()
    shutil.copytree(site, stage, ignore=shutil.ignore_patterns('.git', '_site', '.qbs-local', '.qbs-local.json', 'node_modules', '__pycache__', '.gems', 'vendor', '.bundle'))
    original = Path(release['source'])
    saved = job / original.name
    shutil.copy2(original, saved)
    if digest(saved) != release['source_sha256'] or digest(original) != release['source_sha256']:
        raise SourceError('QBS changed while being copied. Retry after the save finishes.')
    runtime = Path(config['runtime_directory']).expanduser()
    python = runtime / 'python/bin/python3'
    node = runtime / 'node/bin/node'
    env = os.environ.copy()
    env['PYTHONPATH'] = str(work / 'python') + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    extracted = job / 'source.json'
    run([python, site / 'scripts/qds/extract_qds.py', saved, extracted], env=env)
    source = json.loads(extracted.read_text())
    source['importedOn'] = datetime.datetime.now(ZoneInfo(config.get('timezone', 'UTC'))).date().isoformat()
    extracted.write_text(json.dumps(source, ensure_ascii=False))
    # One maintained builder, copied into the isolated runtime directory for module resolution.
    shutil.copy2(site / 'scripts/qds/build_qds.mjs', job / 'build_qds.mjs')
    (job / 'node_modules').symlink_to(runtime / 'node/node_modules', target_is_directory=True)
    marker = Path(config['artifact_marker']).expanduser()
    if not marker.is_file():
        raise SourceError('Artifact Tool operation marker is unavailable; locate the bundled skill marker before building.')
    run([node, marker, '--operation-kind', 'create', '--expected-output-count', str(len(source['tables'])), '--output-format', 'xlsx'])
    run([node, job / 'build_qds.mjs', extracted, stage, review])
    run([python, site / 'scripts/qds/verify_qds.py', extracted, stage, review], env=env)
    # Inspect the original again before declaring this release ready.
    if digest(original) != release['source_sha256']:
        raise SourceError('QBS changed during generation. Keep this run for review and prepare again.')
    edition = source['edition']
    paths = ['qds/index.html', '_datasets/quarterly-statistics.md']
    paths += [str(p.relative_to(stage)) for p in sorted((stage / 'qds').glob(edition + '-*.html'))]
    paths += [str(p.relative_to(stage)) for p in sorted((stage / 'assets/datasets/qds' / edition).iterdir())]
    if len(paths) != 3 + 3 * len(source['tables']):
        raise SourceError('Unexpected generated file count; inspect the prepared release.')
    result = {**release, 'status': 'prepared', 'stage': str(stage), 'review': str(review),
              'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=site).decode().strip(),
              'files': {p: digest(stage / p) for p in paths}}
    (job / 'release.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def apply_release(site, release_path):
    release_path = Path(release_path).resolve()
    release_path.relative_to((site / '.qbs-local').resolve())
    release = json.loads(release_path.read_text())
    if release['status'] != 'prepared':
        raise SourceError('Release has not passed preparation.')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=site).strip():
        raise SourceError('Website checkout has uncommitted changes. Do not overwrite them.')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=site).decode().strip()
    if head != release['base_commit'] or digest(release['source']) != release['source_sha256']:
        raise SourceError('Website or QBS source changed since preparation; prepare again.')
    stage = Path(release['stage']).resolve()
    stage.relative_to(release_path.parent)
    edition = release['edition']
    allowed = {'qds/index.html', '_datasets/quarterly-statistics.md'}
    for name, sha in release['files'].items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts:
            raise SourceError('Invalid release path.')
        valid = name in allowed or (path.parent == Path('qds') and path.name.startswith(edition + '-table-') and path.suffix == '.html') or (path.parent == Path('assets/datasets/qds') / edition and (path.name == 'manifest.json' or path.suffix in ('.xlsx', '.csv')))
        if not valid or digest(stage / path) != sha:
            raise SourceError('Prepared output changed or contains an unexpected file.')
    for name in release['files']:
        destination = site / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + '.qbs-tmp')
        shutil.copy2(stage / name, temporary)
        temporary.replace(destination)
    return {'status': 'applied', 'edition': edition, 'files': len(release['files']), 'release': str(release_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=SITE / '.qbs-local.json')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--check', action='store_true')
    modes.add_argument('--prepare', action='store_true')
    modes.add_argument('--apply', type=Path, metavar='RELEASE_JSON')
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text())
        result = apply_release(SITE, args.apply) if args.apply else inspect_release(SITE, config)
        if args.prepare:
            result = prepare(SITE, config, result)
        print(json.dumps(result, indent=2))
    except (SourceError, ValueError, OSError, subprocess.CalledProcessError) as error:
        print(json.dumps({'status': 'needs_attention', 'message': str(error)}))
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
