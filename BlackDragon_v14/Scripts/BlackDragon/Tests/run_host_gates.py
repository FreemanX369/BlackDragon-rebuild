#!/usr/bin/env python3
"""Reproducible host verification only; does not compile or run MQL5/MT5.

Requires Python 3 and g++ with C++17/UBSan. Never installs dependencies.
Mutation compilation errors are INVALID, never counted as killed defects.
"""
from pathlib import Path
import argparse
import concurrent.futures
import hashlib
import json
import re
import subprocess
import sys
import time

TEST = Path(__file__).resolve().parent
REPO = TEST.parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(command, log):
    p = subprocess.run(command, text=True, capture_output=True)
    log.write_text(p.stdout + p.stderr)
    return p.returncode, p.stdout + p.stderr


def green(code, text):
    return code == 0 and bool(re.search(r'ALL GREEN|SOURCE CONTRACT GREEN|\b0 failed\b', text))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--extended-only', action='store_true', help='CI: regression/source contracts ran in preceding steps')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    workflow = (REPO / '.github/workflows/verify-current.yml').read_text()
    suites = re.search(r'suites=\((.*?)\)', workflow, re.S).group(1).split()
    contracts = [f't{n}_source_contract.py' for n in range(1711, 1725) if n != 1718]
    contracts += ['t1718_headless_source_contract.py', 'repository_contract.py', 't1725_source_contract.py', 't1726_source_contract.py', 'compare_benchmark_test.py']
    regression = out / 'regression'
    regression.mkdir(exist_ok=True)

    def check(name):
        commands = []
        if name.endswith('.cpp'):
            binary = regression / Path(name).stem
            command = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-I', str(REPO / 'BlackDragon_v14/Include'), str(TEST / name), '-o', str(binary)]
            commands.append(command)
            code, text = execute(command, regression / (name + '.compile.log'))
            if code:
                return dict(name=name, status='FAIL', phase='compile', commands=commands, exit_code=code)
            command = [str(binary)]
        else:
            command = [sys.executable, str(TEST / name)]
        commands.append(command)
        code, text = execute(command, regression / (name + '.log'))
        return dict(name=name, status='PASS' if green(code, text) else 'FAIL', commands=commands, exit_code=code)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        checks = list(pool.map(check, [] if args.extended_only else suites + contracts))
    (regression / 'results.json').write_text(json.dumps(checks, indent=2))
    print('Regression:', sum(x['status'] == 'PASS' for x in checks), '/', len(checks), flush=True)
    integrations = []
    for script, folder, expected_fixtures, expected_assertions in [('t1724_integration.py', 'integration', 3, 64), ('t1724_gate_integration.py', 'extra', 3, 53), ('t1725_integration.py', 't1725', 6, 115), ('t1726_integration.py', 't1726', 1, 132)]:
        command = [sys.executable, str(TEST / script), '--out', str(out / folder)]
        code, text = execute(command, out / (folder + '.log'))
        counts = re.findall(r'\b(\d+) passed, (\d+) failed', text)
        passed_assertions = sum(int(p) for p, f in counts)
        failed_assertions = sum(int(f) for p, f in counts)
        complete = len(counts) == expected_fixtures and passed_assertions == expected_assertions and failed_assertions == 0
        integrations.append(dict(name=script, commands=[command], exit_code=code, status='PASS' if green(code, text) and complete else 'FAIL', assertions_passed=passed_assertions, assertions_failed=failed_assertions, expected_fixtures=expected_fixtures, expected_assertions=expected_assertions))
        print(text, end='', flush=True)

    mutations = []
    sanitizers = []
    if all(x['status'] == 'PASS' for x in integrations):
        # Each mutation is made in an isolated generated fixture, never production.
        definitions = [
            ('M01_unfunded', 'integration/protection_integration.cpp', 'return PY_DRIVE_WAIT_UNFUNDED;', 'return PY_DRIVE_NEXT;', None),
            ('M02_reject_cleanup', 'integration/protection_integration.cpp', 'EraseOperationAt(found);', '/* injected: no cleanup */', None),
            ('M03_replay_direction', 't1725/arcs_replay.cpp', 'r.dir=Idx(direction);', 'r.dir=0;', None),
            ('M04_cash_fee', 'integration/cash_integration.cpp', 'return profit+swap+commission+fee;', 'return profit+swap+commission;', 'include/BlackDragon/CashLedger.mqh'),
            ('M05_commission_identity', 'extra/accounting_host.cpp', 'HistorySelectByPosition(s.pos[i].positionId)', 'HistorySelectByPosition(s.pos[i].ticket)', None),
            ('M06_retry_budget', 'extra/persistence_host.cpp', 'm_retry[d].reconcile!=(m_retry[d].rejects>=8)', 'false', None),
            ('M07_adx_invalid', 'extra/adx_host.cpp', 'if(!MathIsValidNumber(adx[0]) || adx[0]==EMPTY_VALUE)\n         return false;', '/* injected: accepts invalid data */', None),
            ('M08_receipt_delta', 't1725/arcs_replay.cpp', 'if(known&&!ApplyReceiptEffect(old,-1,why))return false;', '/* injected: no reversal */', None),
            ('M09_early_ack', 't1725/outcome_store.cpp', 'if(m_records[i].state!=BD_OUT_APPLIED && m_records[i].state!=BD_OUT_PARTIAL && m_records[i].state!=BD_OUT_NO_EFFECT)return false;', '/* injected: ACK unknown */', None),
            ('M10_early_terminal', 't1725/execution_outcomes.cpp', 'if(Journal_StateResolved(m_journal[i]))Journal_CompleteAt(i);', 'Journal_CompleteAt(i);', None),
            ('M11_campaign_duplicate', 't1725/campaign_incremental.cpp', 'if(at>=0){m_deals[at]=r;return true;}', '/* injected: keep duplicate */', None),
            ('M12_sl_fill_identity', 't1726/t1726_protective.cpp', 'return programmedMatch;', 'return programmedMatch && MathAbs(dealPrice-durableTargetSl)<=0.682;', None),
            ('M13_drop_sl_receipt', 't1726/t1726_protective.cpp', 'receipt.protectiveSl=true;', 'receipt.protectiveSl=false;', None),
            ('M14_cursor_skips_late_sl', 't1726/t1726_protective.cpp', 'if(known&&!receipt.deleted&&(receipt.protectiveSl||receipt.pyTrim))continue;', 'if(known&&!receipt.deleted&&(receipt.protectiveSl||receipt.pyTrim))continue; if(!CursorAfter(HistoryDealGetInteger(deal,DEAL_TIME_MSC),deal,m_dir[di].lastDealTimeMsc,m_dir[di].lastDealTicket))continue;', None),
        ]

        def mutate(definition):
            name, source, before, after, header = definition
            original = out / source
            folder = out / 'mutations' / name
            folder.mkdir(parents=True, exist_ok=True)
            cpp = folder / original.name
            cpp.write_bytes(original.read_bytes())
            target = original.parent / header if header else original
            content = target.read_text()
            if content.count(before) != 1:
                return dict(name=name, status='INVALID', reason='mutation target must match exactly once')
            changed = folder / header if header else cpp
            changed.parent.mkdir(parents=True, exist_ok=True)
            changed.write_text(content.replace(before, after, 1))
            command = ['g++', '-std=c++17', '-O1', str(cpp), '-I', str(folder / 'include'), '-I', str(original.parent / 'include'), '-o', str(folder / 'mutant')]
            code, text = execute(command, folder / 'compile.log')
            result = dict(name=name, source=source, original_sha256=sha(target), mutated_sha256=sha(changed), commands=[command], compile_exit_code=code, status='INVALID')
            if code == 0:
                command = [str(folder / 'mutant')]
                result['commands'].append(command)
                code, text = execute(command, folder / 'runtime.log')
                result.update(runtime_exit_code=code, failed_assertions=re.findall(r'^FAIL: (.+)', text, re.M))
                result['status'] = 'KILLED' if code != 0 and result['failed_assertions'] else ('SURVIVED' if code == 0 else 'INVALID')
            return result

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            mutations = list(pool.map(mutate, definitions))
        (out / 'mutations/results.json').write_text(json.dumps(mutations, indent=2))
        print('Mutations:', [(x['name'], x['status']) for x in mutations], flush=True)

        def sanitize(cpp):
            folder = out / 'sanitizers'
            folder.mkdir(exist_ok=True)
            binary = folder / cpp.stem
            command = ['g++', '-std=c++17', '-O1', '-g', '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all', str(cpp), '-I', str(cpp.parent / 'include'), '-o', str(binary)]
            code, text = execute(command, folder / (cpp.stem + '.compile.log'))
            result = dict(name=cpp.stem, source_sha256=sha(cpp), commands=[command], compile_exit_code=code, status='FAIL')
            if code == 0:
                command = [str(binary)]
                result['commands'].append(command)
                code, text = execute(command, folder / (cpp.stem + '.log'))
                result.update(exit_code=code, status='PASS' if green(code, text) and 'runtime error:' not in text else 'FAIL')
            return result

        fixtures = sorted((out / 'integration').glob('*.cpp')) + sorted((out / 'extra').glob('*.cpp')) + sorted((out / 't1725').glob('*.cpp')) + sorted((out / 't1726').glob('*.cpp'))
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            sanitizers = list(pool.map(sanitize, fixtures))
        (out / 'sanitizers/results.json').write_text(json.dumps(sanitizers, indent=2))
        print('UBSan/bounds:', sum(x['status'] == 'PASS' for x in sanitizers), '/', len(sanitizers), flush=True)

    passed = (all(x['status'] == 'PASS' for x in checks + integrations + sanitizers)
              and len(mutations) == 14 and all(x['status'] == 'KILLED' for x in mutations)
              and len(sanitizers) == 13)
    source_files = sorted(p for root in ['Experts', 'Include', 'Scripts'] for p in (REPO / 'BlackDragon_v14' / root).rglob('*') if p.is_file() and p.suffix in {'.mq5', '.mqh', '.py', '.cpp', '.hpp', '.ps1'})
    result = dict(schema='bd-host-gates/1', status='PASS' if passed else 'FAIL', native=False, scope='extended' if args.extended_only else 'full_host',
                  native_compile='DEFERRED_BY_OWNER', native_runtime='NOT_RUN', benchmark='NOT_RUN', release_eligible=False,
                  elapsed_seconds=round(time.time() - started, 3),
                  compiler=subprocess.check_output(['g++', '--version'], text=True).splitlines()[0],
                  regression=checks, integration=integrations, mutations=mutations, sanitizers=sanitizers,
                  source_files=[dict(path=str(p.relative_to(REPO)), sha256=sha(p)) for p in source_files])
    (out / 'HOST_GATE_RESULTS.json').write_text(json.dumps(result, indent=2) + '\n')
    print('HOST GATES:', result['status'], '(native gates remain pending)', flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
