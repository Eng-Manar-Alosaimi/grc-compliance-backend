import pandas as pd


def compute_analytics(results_list):
    """
    يحول نتائج التقييم الخام إلى مؤشرات تحليلية.
    """
    df = pd.DataFrame(results_list)
    
    # تحويل الحالة إلى نقاط
    status_scores = {
        "COMPLIANT": 1.0,
        "PARTIAL": 0.5,
        "GAP": 0.0,
        "NO_EVIDENCE": 0.0
    }
    df['score'] = df['status'].map(status_scores).fillna(0.0)
    df['weighted_score'] = df['score'] * df['risk_weight']
    
    # 1. Assessment Score (ليس "Compliance %")
    assessment_score = round((df['score'].mean() * 100), 1)
    
    # 2. Risk-Weighted Assessment Score
    total_weight = df['risk_weight'].sum()
    risk_weighted_score = round(
        (df['weighted_score'].sum() / total_weight * 100) if total_weight > 0 else 0,
        1
    )
    
    # 3. High-Risk Gaps
    high_risk_gaps = df[
        (df['status'].isin(['GAP', 'NO_EVIDENCE'])) &
        (df['risk_weight'] >= 4)
    ]
    risk_exposure = int(high_risk_gaps['risk_weight'].sum())
    
    # 4. Evidence Coverage
    with_evidence = df[df['status'].isin(['COMPLIANT', 'PARTIAL'])]
    evidence_coverage = round(
        (len(with_evidence) / len(df) * 100) if len(df) > 0 else 0,
        1
    )
    
    # 5. تحليل حسب الفئة
    by_category = df.groupby('category').agg(
        total=('id', 'count'),
        compliant=('status', lambda x: (x == 'COMPLIANT').sum()),
        gaps=('status', lambda x: x.isin(['GAP', 'NO_EVIDENCE']).sum()),
        avg_score=('score', 'mean')
    ).reset_index()
    by_category['compliance_pct'] = (by_category['avg_score'] * 100).round(1)
    
    # 6. توزيع الحالات
    status_distribution = df['status'].value_counts().to_dict()
    
    return {
        "assessment_score": assessment_score,
        "risk_weighted_score": risk_weighted_score,
        "risk_exposure": risk_exposure,
        "evidence_coverage": evidence_coverage,
        "total_requirements": len(df),
        "total_gaps": int(df['status'].isin(['GAP', 'NO_EVIDENCE']).sum()),
        "high_risk_gaps": high_risk_gaps[
            ['id', 'category', 'requirement', 'risk_weight', 'criticality', 'reason']
        ].to_dict(orient='records'),
        "by_category": by_category.to_dict(orient='records'),
        "status_distribution": status_distribution
    }