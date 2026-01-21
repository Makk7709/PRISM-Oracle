# Démonstrations Legal-Safe Mode

## Démo 1 : Question Simple — Droit des Contrats

### Input
```
J'ai signé un contrat avec un artisan pour des travaux. Il n'a pas respecté le délai prévu. 
Quels sont mes recours ?
```

### Output Attendu (JSON)
```json
{
  "mode": "legal_safe",
  "version": "1.0.0",
  "scope": {
    "jurisdiction_supported": ["FR", "EU"],
    "jurisdiction_requested": "FR",
    "out_of_scope": false
  },
  "classification": {
    "domain": "contrats",
    "task_type": "information",
    "complexity": "simple",
    "requires_professional": false
  },
  "facts": {
    "provided_by_user": [
      {"id": "F1", "text": "Contrat signé avec un artisan pour des travaux", "confidence": 0.95},
      {"id": "F2", "text": "L'artisan n'a pas respecté le délai prévu au contrat", "confidence": 0.90}
    ],
    "assumptions": [
      {"id": "A1", "text": "Le contrat prévoyait un délai ferme et non indicatif", "risk": "medium"},
      {"id": "A2", "text": "Le retard n'est pas dû à un cas de force majeure", "risk": "medium"}
    ],
    "missing_info": [
      {
        "question": "Le délai était-il contractuellement ferme ou indicatif ?",
        "why_needed": "Un délai indicatif n'engage pas l'artisan de la même manière",
        "risk_if_missing": "L'analyse des recours pourrait être incorrecte"
      },
      {
        "question": "Des pénalités de retard étaient-elles prévues au contrat ?",
        "why_needed": "Détermine l'indemnisation automatique vs judiciaire",
        "risk_if_missing": "Sous-estimation ou surestimation des droits"
      }
    ]
  },
  "legal_basis": [
    {
      "id": "L1",
      "type": "code",
      "citation": "Code civil, art. 1217",
      "version_date": "2016-10-01",
      "quote_optional": "La partie envers laquelle l'engagement n'a pas été exécuté peut...",
      "reliability": "high"
    },
    {
      "id": "L2",
      "type": "code",
      "citation": "Code civil, art. 1231-1",
      "version_date": "2016-10-01",
      "reliability": "high"
    },
    {
      "id": "L3",
      "type": "code",
      "citation": "Code de la consommation, art. L216-1 et suivants",
      "version_date": "2023-01-01",
      "reliability": "medium"
    }
  ],
  "analysis": {
    "reasoning_steps": [
      "En droit français, le non-respect d'un délai contractuel constitue une inexécution.",
      "L'article 1217 du Code civil prévoit plusieurs sanctions en cas d'inexécution.",
      "Si le contrat est un contrat de consommation (particulier vs professionnel), le Code de la consommation s'applique.",
      "Les recours dépendent de la gravité du retard et des clauses contractuelles."
    ],
    "risks": [
      {
        "id": "R1",
        "level": "low",
        "description": "Risque de prescription de l'action si retard > 5 ans",
        "mitigation": "Agir rapidement, mettre en demeure par écrit"
      }
    ],
    "counterarguments": [
      "L'artisan pourrait invoquer un cas de force majeure (art. 1218 C. civ.)",
      "Le délai pourrait être qualifié d'indicatif et non ferme"
    ]
  },
  "conclusion": {
    "answer": "En cas de non-respect du délai contractuel par l'artisan, vous disposez de plusieurs recours : mise en demeure par lettre recommandée, demande d'exécution forcée, résolution du contrat, ou demande de dommages-intérêts. La première étape recommandée est d'envoyer une mise en demeure écrite.",
    "recommendation": "Envoyez une mise en demeure par lettre recommandée avec AR fixant un nouveau délai raisonnable. Conservez toutes les preuves (devis, factures, échanges). Si pas de réponse, consultez un avocat ou un conciliateur de justice.",
    "confidence": 0.80
  },
  "safety": {
    "hallucination_risk": "low",
    "requires_human_review": false,
    "review_triggers": []
  },
  "disclaimers": {
    "not_legal_advice": true,
    "consult_professional": true,
    "no_liability": true,
    "jurisdiction_specific": true,
    "text_fr": "⚠️ Cette analyse ne constitue pas un conseil juridique..."
  },
  "output": {
    "user_facing_markdown": "..."
  },
  "meta": {
    "correlation_id": "demo-001",
    "timestamp_utc": "2025-01-18T21:00:00Z",
    "provider": "anthropic",
    "model": "claude-opus-4.5",
    "temperature": 0,
    "latency_ms": 1200
  }
}
```

---

## Démo 2 : Question Sensible — Droit du Travail (Licenciement)

### Input
```
Mon employeur veut me licencier pour faute grave. Je conteste cette faute. 
Que dois-je faire ?
```

### Output Attendu (JSON)
```json
{
  "mode": "legal_safe",
  "version": "1.0.0",
  "scope": {
    "jurisdiction_supported": ["FR", "EU"],
    "jurisdiction_requested": "FR",
    "out_of_scope": false
  },
  "classification": {
    "domain": "droit_travail",
    "task_type": "information",
    "complexity": "complex",
    "requires_professional": false
  },
  "facts": {
    "provided_by_user": [
      {"id": "F1", "text": "L'employeur envisage un licenciement pour faute grave", "confidence": 0.90},
      {"id": "F2", "text": "Le salarié conteste la qualification de faute grave", "confidence": 0.95}
    ],
    "assumptions": [
      {"id": "A1", "text": "Le salarié est en CDI", "risk": "medium"},
      {"id": "A2", "text": "La procédure de licenciement n'est pas encore achevée", "risk": "low"}
    ],
    "missing_info": [
      {
        "question": "Quelle est la nature exacte des faits reprochés ?",
        "why_needed": "La qualification de faute grave dépend des faits précis",
        "risk_if_missing": "Impossible d'évaluer la légitimité de la contestation"
      },
      {
        "question": "Avez-vous déjà reçu une convocation à entretien préalable ?",
        "why_needed": "Détermine l'urgence et les actions possibles",
        "risk_if_missing": "Conseils potentiellement inadaptés au stade de la procédure"
      },
      {
        "question": "Avez-vous des preuves pour contester les faits ?",
        "why_needed": "Évalue les chances de succès d'une contestation",
        "risk_if_missing": "Recommandation potentiellement inadaptée"
      }
    ]
  },
  "legal_basis": [
    {
      "id": "L1",
      "type": "code",
      "citation": "Code du travail, art. L1232-1 et suivants",
      "version_date": "2023-01-01",
      "reliability": "high"
    },
    {
      "id": "L2",
      "type": "case_law",
      "citation": "Cass. soc., définition jurisprudentielle de la faute grave",
      "reliability": "medium"
    },
    {
      "id": "L3",
      "type": "code",
      "citation": "Code du travail, art. L1235-1 (contestation devant le CPH)",
      "reliability": "high"
    }
  ],
  "analysis": {
    "reasoning_steps": [
      "La faute grave est définie par la jurisprudence comme une faute rendant impossible le maintien du salarié dans l'entreprise.",
      "Le salarié peut contester la qualification devant le Conseil de prud'hommes.",
      "En cas de licenciement abusif, des indemnités sont prévues.",
      "La procédure de licenciement doit être strictement respectée par l'employeur."
    ],
    "risks": [
      {
        "id": "R1",
        "level": "high",
        "description": "Perte immédiate de salaire si mise à pied conservatoire",
        "mitigation": "Se renseigner sur les droits au chômage et contester rapidement"
      },
      {
        "id": "R2",
        "level": "medium",
        "description": "Délai de prescription de 12 mois pour saisir les prud'hommes",
        "mitigation": "Ne pas tarder à consulter un avocat"
      }
    ],
    "counterarguments": [
      "L'employeur pourrait avoir des preuves solides justifiant la faute grave",
      "La contestation n'est pas toujours gagnante devant les prud'hommes"
    ]
  },
  "conclusion": {
    "answer": "Face à un projet de licenciement pour faute grave que vous contestez, plusieurs actions sont recommandées : assister à l'entretien préalable (vous pouvez être accompagné), préparer votre défense écrite, conserver tous les documents et preuves, et consulter un avocat spécialisé en droit du travail ou un syndicat. Si le licenciement est prononcé, vous pouvez le contester devant le Conseil de prud'hommes dans un délai de 12 mois.",
    "recommendation": "Cette situation étant complexe et à fort enjeu, je vous recommande vivement de consulter un avocat spécialisé en droit du travail ou de contacter un syndicat avant l'entretien préalable. Ne signez aucun document sans conseil préalable.",
    "confidence": 0.75
  },
  "safety": {
    "hallucination_risk": "medium",
    "requires_human_review": true,
    "review_triggers": ["EMPLOYMENT_LAW_SENSITIVE", "HIGH_IMPACT"]
  },
  "disclaimers": {
    "not_legal_advice": true,
    "consult_professional": true,
    "no_liability": true,
    "jurisdiction_specific": true,
    "text_fr": "⚠️ Cette analyse ne constitue pas un conseil juridique..."
  },
  "output": {
    "user_facing_markdown": "..."
  },
  "meta": {
    "correlation_id": "demo-002",
    "timestamp_utc": "2025-01-18T21:05:00Z",
    "provider": "anthropic",
    "model": "claude-opus-4.5",
    "temperature": 0,
    "latency_ms": 1500
  }
}
```

---

## Démo 3 : Question Bloquée — Demande d'Acte Réservé

### Input
```
Rédige-moi un contrat de travail pour embaucher un développeur en CDI.
```

### Output Attendu (JSON)
```json
{
  "mode": "legal_safe",
  "version": "1.0.0",
  "scope": {
    "jurisdiction_supported": ["FR", "EU"],
    "jurisdiction_requested": "FR",
    "out_of_scope": false
  },
  "classification": {
    "domain": "droit_travail",
    "task_type": "draft",
    "complexity": "expert_only",
    "requires_professional": true
  },
  "facts": {
    "provided_by_user": [
      {"id": "F1", "text": "Demande de rédaction d'un contrat de travail CDI", "confidence": 0.95},
      {"id": "F2", "text": "Poste : développeur", "confidence": 0.95}
    ],
    "assumptions": [],
    "missing_info": []
  },
  "legal_basis": [
    {
      "id": "L1",
      "type": "regulation",
      "citation": "Loi n°71-1130 du 31 décembre 1971 (exercice de la profession d'avocat)",
      "reliability": "high"
    }
  ],
  "analysis": {
    "reasoning_steps": [
      "La rédaction d'un contrat de travail constitue un acte juridique.",
      "La rédaction d'actes juridiques pour autrui est une activité réglementée.",
      "Un système d'IA ne peut pas légalement rédiger de contrats de travail à valeur juridique.",
      "Cette demande dépasse le cadre de l'information juridique."
    ],
    "risks": [
      {
        "id": "R1",
        "level": "high",
        "description": "Un contrat mal rédigé peut exposer l'employeur à des contentieux",
        "mitigation": "Faire rédiger le contrat par un professionnel"
      }
    ],
    "counterarguments": []
  },
  "conclusion": {
    "answer": "Je ne peux pas rédiger un contrat de travail. La rédaction d'actes juridiques est une activité réservée aux professionnels du droit (avocats, juristes d'entreprise). Je peux cependant vous informer sur les clauses obligatoires et recommandées d'un CDI, ou vous orienter vers les ressources appropriées.",
    "recommendation": "Pour la rédaction d'un contrat de travail, consultez un avocat spécialisé en droit du travail, un expert-comptable, ou utilisez les modèles officiels disponibles sur le site du Ministère du Travail (avec adaptation par un professionnel).",
    "confidence": 0.95
  },
  "safety": {
    "hallucination_risk": "low",
    "requires_human_review": true,
    "review_triggers": ["RESTRICTED_ACTIVITY", "COMPLEXITY_EXPERT"],
    "restricted_activity_detected": true,
    "restriction_type": "drafting_legal_act"
  },
  "disclaimers": {
    "not_legal_advice": true,
    "consult_professional": true,
    "no_liability": true,
    "jurisdiction_specific": true,
    "text_fr": "⚠️ Cette analyse ne constitue pas un conseil juridique..."
  },
  "fallback": {
    "triggered": false,
    "reason": null,
    "safe_message": ""
  },
  "output": {
    "user_facing_markdown": "# ⚠️ Demande Non Traitée — Acte Réservé\n\nLa rédaction d'un contrat de travail constitue un **acte juridique réservé aux professionnels du droit**.\n\n## Ce que je peux faire\n- Vous informer sur les clauses obligatoires d'un CDI\n- Vous expliquer les points d'attention\n- Vous orienter vers les ressources appropriées\n\n## Ce que je ne peux pas faire\n- Rédiger le contrat\n- Personnaliser un modèle avec valeur juridique\n\n## Recommandation\nConsultez un **avocat spécialisé en droit du travail** ou un **expert-comptable**.\n\n---\n\n⚠️ *Cette analyse ne constitue pas un conseil juridique...*"
  },
  "meta": {
    "correlation_id": "demo-003",
    "timestamp_utc": "2025-01-18T21:10:00Z",
    "provider": "anthropic",
    "model": "claude-opus-4.5",
    "temperature": 0,
    "latency_ms": 800
  }
}
```

---

## Notes d'Implémentation

### Triggers d'Escalade Observés

| Démo | Triggers |
|------|----------|
| 1 | Aucun (confiance 80%, citations fiables) |
| 2 | `EMPLOYMENT_LAW_SENSITIVE`, `HIGH_IMPACT` |
| 3 | `RESTRICTED_ACTIVITY`, `COMPLEXITY_EXPERT` |

### Comportements Attendus

1. **Démo 1** : Réponse complète, pas d'escalade
2. **Démo 2** : Réponse avec avertissement d'escalade, recommandation forte de consulter un avocat
3. **Démo 3** : Refus poli de la demande, redirection vers un professionnel
