"""Narration script for the Julius Caesar TikTok video.

Each scene has an id (used by render.py to pick the animation), a year label
for the timeline HUD, and the narration text. Words wrapped as {text|phonemes}
are spoken with the given IPA phonemes (fixes Latin names the TTS mangles);
on-screen captions show only the text part.

Sources: Suetonius, Divus Julius; Plutarch, Life of Caesar / Life of Pompey;
Caesar, Bellum Gallicum and Bellum Civile; Cassius Dio, books 37-44.
"""

SCENES = [
    dict(id="hook", year=-49, text=(
        "January, 49 B.C. A Roman general halts his army at a small river. "
        "Cross it, and he commits treason. Stay, and he's finished. How did "
        "Julius Caesar get here?")),
    dict(id="origins", year=-100, text=(
        "Born in 100 B.C., Caesar came from an old family that claimed "
        "descent from Venus, but had little money or power. His "
        "aunt married Marius, Rome's great populist general.")),
    dict(id="sulla", year=-82, text=(
        "That link nearly killed him. When Marius's rival Sulla seized Rome, "
        "he ordered young Caesar to divorce his wife. Caesar refused, and hid "
        "until allies won his pardon.")),
    dict(id="pirates", year=-75, text=(
        "Around 75 B.C., pirates kidnapped him and demanded 20 talents. "
        "Caesar, insulted, told them to ask for 50. Once freed, he hunted "
        "them down and crucified them, as promised.")),
    dict(id="ladder", year=-63, text=(
        "Back in Rome he climbed the ladder of offices on borrowed money. In "
        "63 B.C., drowning in debt, he was elected Pontifex Maximus, Rome's "
        "chief priest.")),
    dict(id="triumvirate", year=-60, text=(
        "In 60 B.C. came his boldest move: a secret pact with Pompey the "
        "Great, Rome's most famous general, and Marcus Crassus, its richest "
        "man. The First Triumvirate.")),
    dict(id="deal", year=-59, text=(
        "Pompey wanted land for his veterans. Crassus wanted favors for his "
        "business allies. Caesar wanted the consulship. Pompey even married "
        "Caesar's daughter, Julia.")),
    dict(id="consul", year=-59, text=(
        "As consul in 59, Caesar rammed their laws through so brazenly that "
        "his colleague {Bibulus|bˈɪbjʊləs} hid at home. Romans called it the "
        "consulship of Julius and Caesar.")),
    dict(id="gaul", year=-58, text=(
        "His prize: command of Gaul. For eight years he campaigned beyond the "
        "Alps. He bridged the Rhine in about ten days, and crossed to "
        "Britain, twice.")),
    dict(id="alesia", year=-52, text=(
        "At Alesia in 52 B.C., he trapped the Gallic leader Vercingetorix "
        "inside two rings of siege walls, one facing in, one facing out. "
        "Vercingetorix surrendered. Gaul was conquered.")),
    dict(id="legions", year=-50, text=(
        "Now Caesar was rich, wildly popular, and commanded battle-hardened "
        "legions loyal to him. The Senate was terrified.")),
    dict(id="collapse", year=-53, text=(
        "And the alliance was dying. In 54 B.C., Julia died in childbirth. In "
        "53, Crassus was killed by the Parthians at Carrhae. Pompey drifted "
        "to Caesar's enemies.")),
    dict(id="ultimatum", year=-49, text=(
        "They planned to strip Caesar of his army and prosecute him. In "
        "January 49, the Senate ordered him to disband his legions or be "
        "declared a public enemy. Mark Antony vetoed, and fled to Caesar.")),
    dict(id="rubicon", year=-49, text=(
        "Roman law forbade a governor to bring his army into Italy. The "
        "border was the Rubicon. With one legion, the Thirteenth, Caesar "
        "crossed. {Alea iacta est|ˈɑːlɛɑː jˈɑːktɑː ˈɛst}. The die is cast.")),
    dict(id="italy", year=-49, text=(
        "Pompey had boasted he could raise legions by stamping his foot. "
        "Instead he fled Rome, then Italy, sailing for Greece. In about two "
        "months Caesar held Italy, pardoning his enemies.")),
    dict(id="spain", year=-49, text=(
        "Next, Spain. I go to fight an army without a leader, he said, then a "
        "leader without an army. Pompey's legions there surrendered that "
        "summer.")),
    dict(id="dyrrhachium", year=-48, text=(
        "In Greece, Pompey beat Caesar at {Dyrrhachium|dɪɹˈeɪkiəm}, but "
        "didn't finish him. The enemy would have won, Caesar said, if they "
        "had a commander who knew how to win.")),
    dict(id="pharsalus", year=-48, text=(
        "August 48 B.C. {Pharsalus|fɑːɹsˈeɪləs}. Caesar's 22,000 men faced "
        "about 45,000. When Pompey's cavalry charged, a hidden fourth line of "
        "infantry broke them. Pompey's army collapsed.")),
    dict(id="egypt", year=-48, text=(
        "Pompey fled to Egypt. The boy king {Ptolemy's|tˈɑːləmiz} advisers "
        "had him stabbed as he came ashore. When Caesar arrived, they gave "
        "him Pompey's head. Caesar wept.")),
    dict(id="epilogue", year=-45, text=(
        "Caesar fought on. Egypt and Cleopatra. Zela: I came, I saw, I "
        "conquered. Thapsus. Munda. In 44 B.C., he became dictator for life.")),
    dict(id="ides", year=-44, text=(
        "Weeks later, on the {Ides|ˈaɪdz} of March, senators stabbed him 23 "
        "times, at the foot of a statue of Pompey.")),
    dict(id="outro", year=-44, text=(
        "One river crossing. Five years of civil war. And a "
        "five-hundred-year-old Republic never recovered.")),
]
