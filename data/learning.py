"""Learning unlocks derived from lifetime XP, including existing progress."""
STAGES = [
    dict(xp=0, title="Les premiers mots", categories=["Premiers mots", "Au quotidien", "À table"]),
    dict(xp=60, title="Rencontrer et écouter", categories=["Les personnes", "Les pronoms", "Questions"]),
    dict(xp=150, title="Vivre et écrire", categories=["Loisirs", "Météo et soirée", "Les verbes"]),
    dict(xp=300, title="Assembler les mots", categories=["Petits mots", "Expressions", "Les possessifs"]),
    dict(xp=500, title="Comprendre les phrases", categories=["Être au présent", "Avoir au présent", "Phrases et intonation"]),
    dict(xp=750, title="Se repérer dans l’espace", categories=["Les prépositions"]),
]
MODE_XP = {"quiz": 0, "copy": 0, "review": 0, "listen_quiz": 60, "type": 150, "mixed": 300, "dictation": 500}
TOPIC_XP = {category: stage["xp"] for stage in STAGES for category in stage["categories"]}


def learning_state(xp, enabled=True):
    stages = [dict(stage, number=index+1, unlocked=not enabled or xp >= stage["xp"], remaining=max(0, stage["xp"]-xp))
              for index, stage in enumerate(STAGES)]
    current = next(stage for stage in reversed(stages) if stage["unlocked"])
    following = next((stage for stage in stages if not stage["unlocked"]), None)
    return dict(xp=xp, stages=stages, current=current, following=following,
                percent=min(100, round((xp-current["xp"])/(following["xp"]-current["xp"])*100)) if following else 100,
                modes={mode:dict(xp=required, unlocked=not enabled or xp>=required, remaining=max(0,required-xp)) for mode,required in MODE_XP.items()},
                topics={topic:dict(xp=required, unlocked=not enabled or xp>=required, remaining=max(0,required-xp)) for topic,required in TOPIC_XP.items()})
