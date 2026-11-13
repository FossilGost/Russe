"""Letter names and contextual examples; extra words are labelled in the UI."""

# letter, French sound guide, spoken Russian name, example, French fallback
LETTER_ROWS = [
    ("А", "a", "а", "а́том", "l’atome"),
    ("Б", "b", "бэ", "брат", "le frère"),
    ("В", "v", "вэ", "вода́", "l’eau"),
    ("Г", "g", "гэ", "год", "l’année"),
    ("Д", "d", "дэ", "дом", "la maison"),
    ("Е", "ié", "е", "ве́тер", "le vent"),
    ("Ё", "io", "ё", "её", "son / sa (à elle)"),
    ("Ж", "j", "жэ", "жить", "habiter, vivre"),
    ("З", "z", "зэ", "зонт", "le parapluie"),
    ("И", "i", "и", "кит", "la baleine"),
    ("Й", "ï", "и краткое", "чай", "le thé"),
    ("К", "k", "ка", "кот", "le chat"),
    ("Л", "l", "эль", "слу́шать", "écouter"),
    ("М", "m", "эм", "ма́ма", "la maman"),
    ("Н", "n", "эн", "но́вый", "nouveau"),
    ("О", "o", "о", "кот", "le chat"),
    ("П", "p", "пэ", "па́па", "le papa"),
    ("Р", "r roulé", "эр", "рука́", "la main"),
    ("С", "s", "эс", "сок", "le jus"),
    ("Т", "t", "тэ", "там", "là-bas"),
    ("У", "ou", "у", "су́мка", "le sac"),
    ("Ф", "f", "эф", "фо́то", "la photo"),
    ("Х", "kh", "ха", "хорошо́", "bien"),
    ("Ц", "ts", "цэ", "конце́рт", "le concert"),
    ("Ч", "tch", "чэ", "чай", "le thé"),
    ("Ш", "ch", "ша", "маши́на", "la voiture"),
    ("Щ", "ch long et adouci", "ща", "щу́ка", "le brochet"),
    ("Ъ", "signe dur", "твёрдый знак", "подъе́зд", "l’entrée d’un immeuble"),
    ("Ы", "son ы (sans équivalent exact en français)", "ы", "мы", "nous"),
    ("Ь", "signe mou", "мягкий знак", "мать", "la mère"),
    ("Э", "è", "э", "э́то", "c’est / ceci"),
    ("Ю", "iou", "ю", "юг", "le sud"),
    ("Я", "ia", "я", "язы́к", "la langue"),
]

LETTERS = [dict(letter=letter, sound=sound, name=name, example=example, fr=fr)
           for letter, sound, name, example, fr in LETTER_ROWS]
BY_LETTER = {entry["letter"]: entry for entry in LETTERS}
