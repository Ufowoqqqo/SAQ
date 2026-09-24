"""Report the frozen completed matrix without selecting or rerunning models."""
import csv
from pathlib import Path

root = Path(__file__).resolve().parent
run = root / 'strong_baselines_v1'
with (run / 'summary.tsv').open() as data:
    rows = list(csv.DictReader(data, delimiter='\t'))
assert len(rows) == 48
lookup = {(r['dataset'], r['fold'], r['plan'], r['arm']): r for r in rows}
assert len(lookup) == 48

def save(name, values):
    with (root / name).open('w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=list(values[0]), delimiter='\t')
        writer.writeheader()
        writer.writerows(values)

matrix, pairing, checks = [], [], []
for dataset in ('SIFT1M', 'GIST1M_HEAD128'):
    for fold in ('A_TO_B', 'B_TO_A'):
        for plan in ('ADJ', 'CORR_GREEDY', 'EA'):
            arms = {a: lookup[dataset, fold, plan, a] for a in 'UVES'}
            assert all(int(r['payload_bits_per_vector']) == 512 for r in arms.values())
            e, s = (float(arms[a]['fit_total_sse']) for a in 'ES')
            assert s <= e + 1e-10 + 1e-12 * abs(e)
            matrix.append(dict(dataset=dataset, fold=fold, plan=plan,
                               **{a: float(arms[a]['eval_sse_per_vector']) for a in 'UVES'}))
            checks.append(dict(dataset=dataset, fold=fold, plan=plan,
                               exact_budget='PASS', constrained_DP='PASS_runtime',
                               S_fit_no_worse_than_E='PASS', fit_S= s, fit_E=e))
        corr = float(lookup[dataset, fold, 'CORR_GREEDY', 'S']['eval_sse_per_vector'])
        pairing.append(dict(dataset=dataset, fold=fold, CORR_S_eval_SSE_per_vector=corr,
                            **{f'gain_vs_{p}_S_percent': 100 * (1 - corr / float(
                                lookup[dataset, fold, p, 'S']['eval_sse_per_vector']))
                               for p in ('ADJ', 'EA')}))
save('absolute_eval_matrix.tsv', matrix)
save('pairing_effects.tsv', pairing)
save('correctness_checks.tsv', checks)
with (run / 'comparisons.tsv').open() as data:
    comparisons = list(csv.DictReader(data, delimiter='\t'))
assert len(comparisons) == 16
for row in comparisons:
    row['gain_percent'] = float(row['gain_fraction']) * 100
save('candidate_comparisons_percent.tsv', comparisons)
upstream = []
for dataset in ('sift', 'gist'):
    panel = root / 'panels' / dataset
    pca = (panel / 'pca.faiss').stat().st_size
    coarse = (panel / 'nlist_1024/coarse.faiss').stat().st_size
    upstream.append(dict(dataset=dataset, full_PCA_serialized_bytes=pca,
                         coarse_serialized_bytes=coarse, total_serialized_bytes=pca+coarse))
save('upstream_model_bytes.tsv', upstream)
print('ABSOLUTE EVALUATION SSE PER VECTOR')
for r in matrix:
    print(f"| {r['dataset']} | {r['fold']} | {r['plan']} | " +
          ' | '.join(f'{r[a]:.9g}' for a in 'UVES') + ' |')
print('PAIRING EFFECTS')
for r in pairing:
    print(r)
print('UPSTREAM SERIALIZED BYTES', upstream)
for key in ('shared_model_total_bytes', 'shared_selected_codebook_bytes', 'selected_lookup_entries'):
    values = [int(r[key]) for r in rows]
    print(key, min(values), max(values))
