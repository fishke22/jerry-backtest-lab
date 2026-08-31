from __future__ import annotations

import csv,hashlib,json,random,statistics
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PRE=ROOT/'config'/'jnu_macd_4_22_3_postpublication_g1_prereg.json'
PANEL=ROOT/'cloud_data'/'derived'/'jnu_macd_4_22_3_mini_stage_a_g1.csv'
MANIFEST=ROOT/'cloud_data'/'manifests'/'jnu_macd_4_22_3_mini_stage_a_g1_manifest.json'
RESULT=ROOT/'directional_results'/'jnu_macd_4_22_3_true_ose_mini_stage_a_g1.json'
REPORT=ROOT/'directional_reports'/'jnu_macd_4_22_3_true_ose_mini_stage_a_g1.md'

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as fh:
        for b in iter(lambda:fh.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def q(xs,p):
    ys=sorted(xs);pos=(len(ys)-1)*p;lo=int(pos);hi=min(lo+1,len(ys)-1);f=pos-lo
    return ys[lo]*(1-f)+ys[hi]*f

def block_bootstrap(xs,block,samples,seed):
    rng=random.Random(seed);n=len(xs);starts=list(range(max(1,n-block+1)));means=[]
    for _ in range(samples):
        z=[]
        while len(z)<n:
            s=rng.choice(starts);z.extend(xs[s:s+block])
        means.append(sum(z[:n])/n)
    prob=sum(x>0 for x in means)/samples
    return {'block_days':block,'samples':samples,'seed':seed,'prob_mean_positive':prob,'one_sided_p':1-prob,'ci95':[q(means,.025),q(means,.975)]}

def main():
    pre=json.loads(PRE.read_text(encoding='utf-8'));m=json.loads(MANIFEST.read_text(encoding='utf-8'))
    if m.get('raw_data_cloud_uploaded') is not False:raise RuntimeError('raw cloud')
    if m.get('critical_data_quality_issues'):raise RuntimeError('critical DQ')
    if m.get('derived_output_hash')!=sha256_file(PANEL):raise RuntimeError('hash mismatch')
    if m.get('stage')!='A_TRUE_OSE_MINI':raise RuntimeError('wrong stage')
    if m.get('market_outcome_interpretation_performed') is not False:raise RuntimeError('local interpretation')
    rows=list(csv.DictReader(PANEL.open(encoding='utf-8')));rets=[float(r['strategy_return']) for r in rows]
    correct=sum(int(r['correct']) for r in rows);denom=sum(int(r['accuracy_denominator']) for r in rows);acc=correct/denom if denom else None
    bcfg=pre['primary_test']['bootstrap'];bs=block_bootstrap(rets,int(bcfg['block_days']),int(bcfg['resamples']),int(bcfg['seed']))
    mean_ret=statistics.fmean(rets) if rets else None;min_days=int(pre['stage_a']['minimum_evaluation_days'])
    positions=[int(r['implemented_position']) for r in rows];trades=sum(1 for i in range(1,len(positions)) if positions[i]!=positions[i-1])
    passed=bool(len(rows)>=min_days and mean_ret is not None and mean_ret>0 and acc is not None and acc>0.5 and bs['prob_mean_positive']>=float(bcfg['probability_mean_strategy_return_positive_threshold']))
    status='TRUE_OSE_MINI_MACD_4_22_3_STAGE_A_PASS' if passed else 'TRUE_OSE_MINI_MACD_4_22_3_STAGE_A_FAIL'
    result={'candidate_id':pre['candidate_id'],'stage':'A_TRUE_OSE_MINI','status':status,'stage_a_pass':passed,'role':'DIRECTIONAL_TRADING_RULE_INFORMATION_GATE','usable_days':len(rows),'minimum_usable_days':min_days,'mean_gross_daily_strategy_return':mean_ret,'aggregate_directional_accuracy_nonzero_targets':acc,'correct_nonzero_targets':correct,'accuracy_denominator':denom,'position_changes_diagnostic':trades,'bootstrap':bs,'derived_panel_sha256':sha256_file(PANEL),'manifest_sha256':sha256_file(MANIFEST),'next_rule':'Proceed to exact JNU Micro Stage B using identical 4,22,3 rule; then mandatory transaction-cost/overfit gates.' if passed else 'Close MACD G1 permanently; do not test parameter/rule variants.','generated_at_utc':datetime.now(timezone.utc).isoformat()}
    RESULT.parent.mkdir(parents=True,exist_ok=True);REPORT.parent.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    REPORT.write_text('# Fixed MACD(4,22,3) post-publication OSE Mini Stage A\n\n'+f'- Status: **{status}**\n- Days: {len(rows)}\n- Mean gross daily strategy return: {mean_ret}\n- Directional accuracy: {acc}\n- Pboot(mean>0): {bs["prob_mean_positive"]}\n- Position changes: {trades}\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
