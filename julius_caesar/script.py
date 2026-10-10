"""On-screen story text for the Julius Caesar TikTok video (no narration).

Each scene has an id (used by render.py to pick the animation), a year label
for the timeline HUD, and the caption text that tells the story. Scene
animations key their beats to words in this text, so keep cue words in sync
with scenes.py when editing.

Sources: Suetonius, Divus Julius; Plutarch, Life of Caesar / Life of Pompey;
Caesar, Bellum Gallicum and Bellum Civile; Cassius Dio, books 37-44.
"""

SCENES = [
    dict(id="hook", year=-49, text=(
        "January, 49 BC. Caesar halts his army at a small river. Cross it: "
        "treason. Stay: ruin. How did he get here?")),
    dict(id="origins", year=-100, text=(
        "Born 100 BC. His old family claimed descent from Venus, but had "
        "little money. His aunt married Marius, the populist general.")),
    dict(id="sulla", year=-82, text=(
        "Marius's rival Sulla took Rome and ordered young Caesar to divorce "
        "his wife. Caesar refused, hid, and was finally pardoned.")),
    dict(id="pirates", year=-75, text=(
        "75 BC: pirates seized him and asked 20 talents. Insulted, he told "
        "them to ask 50. Freed, he hunted them down and crucified them, as "
        "promised.")),
    dict(id="ladder", year=-63, text=(
        "He climbed Rome's ladder of offices on borrowed money. In 63 BC, "
        "deep in debt, he became Pontifex Maximus, chief priest.")),
    dict(id="triumvirate", year=-60, text=(
        "60 BC: a secret pact. Pompey, Rome's most famous general. Crassus, "
        "its richest man. Caesar, the politician. The First Triumvirate.")),
    dict(id="deal", year=-59, text=(
        "Pompey wanted land for veterans. Crassus wanted favors for allies. "
        "Caesar wanted the consulship. Pompey married Caesar's daughter, "
        "Julia.")),
    dict(id="consul", year=-59, text=(
        "As consul in 59 BC, Caesar bulldozed the laws through. His colleague "
        "Bibulus hid at home. Romans joked: the consulship of Julius and "
        "Caesar.")),
    dict(id="gaul", year=-58, text=(
        "His reward: Gaul. Eight years of war beyond the Alps. He bridged the "
        "Rhine in ten days and crossed to Britain twice.")),
    dict(id="alesia", year=-52, text=(
        "52 BC, Alesia. He trapped Vercingetorix inside two rings of walls: "
        "one facing in, one facing out. Vercingetorix surrendered. Gaul was "
        "conquered.")),
    dict(id="legions", year=-50, text=(
        "Now Caesar was rich, popular, and commanded loyal legions. The "
        "Senate was terrified.")),
    dict(id="collapse", year=-53, text=(
        "Then the pact crumbled. 54 BC: Julia died. 53 BC: Crassus was killed "
        "at Carrhae. Pompey drifted to Caesar's enemies.")),
    dict(id="ultimatum", year=-49, text=(
        "His enemies wanted him disarmed and on trial. January 49 BC, the "
        "Senate decreed: disband, or be a public enemy. Antony vetoed, then "
        "fled to Caesar.")),
    dict(id="rubicon", year=-49, text=(
        "The law forbade bringing an army into Italy. The border: the "
        "Rubicon. With one legion, the Thirteenth, Caesar crossed. || Alea iacta "
        "est. The die is cast.")),
    dict(id="italy", year=-49, text=(
        "Pompey boasted he could raise legions by stamping his foot. Instead "
        "he fled to Greece. In two months Caesar held Italy, pardoning his "
        "enemies.")),
    dict(id="spain", year=-49, text=(
        "Next, Spain. First an army without a leader, then a leader without "
        "an army. Pompey's legions there surrendered.")),
    dict(id="dyrrhachium", year=-48, text=(
        "In Greece, Pompey beat Caesar at Dyrrhachium but failed to finish "
        "him off. Caesar slipped away to Thessaly.")),
    dict(id="pharsalus", year=-48, text=(
        "August 48 BC, Pharsalus. Caesar's 22,000 faced about 45,000. "
        "Pompey's cavalry charged, but a hidden fourth line broke them. "
        "Pompey's army collapsed.")),
    dict(id="egypt", year=-48, text=(
        "Pompey fled to Egypt. The boy king's men stabbed him as he came "
        "ashore. Caesar arrived to be handed Pompey's head. He wept.")),
    dict(id="epilogue", year=-45, text=(
        "Caesar fought on. Egypt and Cleopatra. Zela: I came, I saw, I "
        "conquered. Thapsus. Munda. In 44 BC: dictator for life.")),
    dict(id="ides", year=-44, text=(
        "Weeks later, on the Ides of March, senators stabbed him 23 times, at "
        "the foot of Pompey's statue.")),
    dict(id="outro", year=-44, text=(
        "One river crossing. Five years of civil war. And a Republic nearly "
        "five centuries old never recovered.")),
]
