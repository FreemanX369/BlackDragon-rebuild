"""Remove only the exact opt-in metric statement for historical hash checks.

Do not exempt these files from their original full-body preservation checks.
"""
COUNTS = {
    'BlackDragon_v14/Include/BlackDragon/Recovery/RecoveryEngineT13Base.mqh': 1,
    'BlackDragon_v14/Include/BlackDragon/Recovery/RecoveryExit.mqh': 2,
    'BlackDragon_v14/Include/BlackDragon/Recovery/RecoveryLock.mqh': 1,
}
ADDITION = '\n#ifdef BD_DIAGNOSTICS\n      g_bdMetrics.Add(BD_M_SORT_ITEMS,(ulong)ArraySize(items));\n#endif'


def before_diagnostics(path, text):
    if path in COUNTS:
        assert text.count(ADDITION) == COUNTS[path], 'unexpected diagnostic scope: ' + path
        return text.replace(ADDITION, '')
    return text
