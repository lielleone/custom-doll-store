# Draft texts for the legal pages. Not reviewed by a professional yet.
# Text in square brackets is a placeholder for the owner to fill.
# A paragraph is a string, or a list of parts where a part is a string
# or a link dict {"text": ..., "href": ...}.

import re

# True while the texts are drafts: shows the draft banner and adds noindex.
# Set to False only after a professional has reviewed all four pages.
LEGAL_DRAFT = True

LEGAL_PAGES = {
    "terms": {
        "title": "תקנון האתר ותנאי רכישה",
        "paragraphs": [
            "האתר מציע בובות בעיצוב אישי, המיוצרות לפי ציור או תמונה שהלקוח מעלה.",
            "ביצוע הזמנה באתר מהווה הסכמה לתנאים אלה.",
            "מחיר בסיס: 380 שקלים, כולל משלוח עד הבית. רקמה אישית: תוספת של 30 שקלים.",
            "זמן הייצור הוא 10 עד 14 ימי עסקים, וזמן האספקה הכולל הוא 14 עד 21 ימי עסקים מרגע אישור ההזמנה.",
            "אמצעי תשלום: [יושלם בהתאם לספק הסליקה שייבחר]",
            "[יושלם: תנאי אחריות על המוצר]",
            "[יושלם: שם העסק, מספר עוסק וכתובת]",
        ],
    },
    "cancellation": {
        "title": "מדיניות ביטולים והחזרות",
        "paragraphs": [
            "מכיוון שמדובר במוצר שיוצר במיוחד לפי הזמנה אישית וציור ייחודי של הלקוח, לא ניתן לבטל את העסקה או להחזיר את הבובה לאחר שהחל תהליך הייצור והתפירה.",
            "[יושלם לאחר בדיקה משפטית: תנאי הביטול לפני תחילת הייצור, וההתייחסות לחוק הגנת הצרכן]",
        ],
    },
    "privacy": {
        "title": "מדיניות פרטיות",
        "paragraphs": [
            "בעת ביצוע הזמנה אנו אוספים: שם מלא, טלפון, דואר אלקטרוני, כתובת למשלוח, הערות, והציור או התמונה שהועלו.",
            "הציורים והתמונות ישמשו אך ורק לצורך ייצור הבובה, ולא יפורסמו ברשתות החברתיות ללא אישור מפורש ומראש מהלקוח.",
            "[יושלם לאחר בדיקה משפטית: אילו ספקי שירות מקבלים מידע לצורך ביצוע ההזמנה (אחסון, משלוחים, סליקה), משך שמירת המידע, וזכויות העיון והמחיקה]",
        ],
    },
    "accessibility": {
        "title": "הצהרת נגישות",
        "paragraphs": [
            "אנו פועלים להנגשת האתר ולהקלת הגלישה בו לכלל המשתמשים.",
            "בדיקת נגישות מקצועית של האתר טרם בוצעה.",
            [
                "אם נתקלתם בבעיית נגישות, נשמח שתעדכנו אותנו דרך ",
                {"text": "עמוד צור קשר", "href": "/contact"},
                ".",
            ],
            "[יושלם: שם רכז הנגישות, טלפון ודואר אלקטרוני]",
        ],
    },
}


PLACEHOLDER_RE = re.compile(r"\[[^\]]*\]")


def _paragraph_text(paragraph):
    if isinstance(paragraph, str):
        return paragraph
    return "".join(p if isinstance(p, str) else p["text"] for p in paragraph)


def legal_problems():
    """What still keeps the legal pages from being final (empty if ready)."""
    problems = []
    if LEGAL_DRAFT:
        problems.append(
            "Legal pages are still drafts (LEGAL_DRAFT = True in legal.py), "
            "so the draft banner is on."
        )
    for slug, page in LEGAL_PAGES.items():
        for paragraph in page["paragraphs"]:
            for placeholder in PLACEHOLDER_RE.findall(_paragraph_text(paragraph)):
                problems.append(f"/{slug} still has a placeholder: {placeholder}")
    return problems
