"""
Sciences au lycée général (programmes en vigueur en 2026-2027) — notions PROUVÉES.

  python -m pedagogy.ingest.sciences_lycee
Écrit pedagogy/data/notions/{PC,SVT,ES}/<NIVEAU>[_<ENSEIGNEMENT>].json.

Sources (registre officiel, SHA-256 vérifié) :
  SRC-2NDE-PC-2019, SRC-1RE-PC-2019, SRC-TLE-PC-2019     physique-chimie (2nde commun, spécialité 1re/Tle)
  SRC-2NDE-SVT-2019, SRC-1RE-SVT-2019, SRC-TLE-SVT-2019  SVT (2nde commun, spécialité 1re/Tle)
  SRC-1RE-ES-2023, SRC-TLE-ES-2023                       enseignement scientifique (tronc commun 1re/Tle)

Méthode d'extraction
--------------------
Les programmes sont des tableaux à deux colonnes (« Notions et contenus | Capacités exigibles »,
« Connaissances | Capacités, attitudes », « Savoirs | Savoir-faire ») ou, en SVT 2nde/1re, des
blocs « Connaissances » / « Capacités » en une colonne. L'extraction texte brute de pypdf
entremêle parfois les colonnes : on s'appuie donc sur la POSITION de chaque fragment (abscisse,
ordonnée, graisse, corps) pour attribuer chaque ligne à sa colonne et reconnaître les rubriques.

Le libellé retenu n'est jamais reconstruit à partir des fragments : le bloc de chaque colonne
est recherché (sans tenir compte des blancs) dans le texte brut de la page, et c'est la
sous-chaîne correspondante du texte brut qui est découpée en phrases puis soumise à
Builder.add (preuve verbatim sur la page déclarée, puis promote_notion). Un bloc qui n'est pas
contigu dans le texte brut est découpé en segments contigus ; ce qui ne se retrouve pas est
écarté. Aucun libellé n'est inventé, aucun item ne franchit une page.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from pypdf import PdfReader

from pedagogy.ingest.core import Builder, Item, clean_line, link_sequential_prerequisites, report_rejections, write_notion_file
from pedagogy.models import Course, Level, Subject
from pedagogy.registry import DATA_DIR, REPO_ROOT

SCHOOL_YEAR = "2026-2027"
GENERATED_BY = "pedagogy.ingest.sciences_lycee"
MIN_WORDS = 4


# --------------------------------------------------------------------------- #
# Spécifications des documents
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DocSpec:
    source_id: str
    subject: Subject
    level: Level
    course: Course
    out: str                                 # chemin relatif sous data/notions
    program_version: str
    difficulty: int
    domains: Tuple[Tuple[str, str, str], ...]  # (préfixe du titre, code, libellé)
    layout: str                              # "table" | "svt_blocks"
    first_page: int
    left_kind: str
    right_kind: str
    header_keys: Tuple[str, ...]             # en-têtes de tableau (clés compactes)


PC_DOMAINS = (
    ("Mesure et incertitudes", "MESURE", "Mesure et incertitudes"),
    ("Constitution et transformations de la matière", "CTM", "Constitution et transformations de la matière"),
    ("Mouvement et interactions", "MI", "Mouvement et interactions"),
    ("L’énergie : conversions et transferts", "ENERGIE", "L’énergie : conversions et transferts"),
    ("Ondes et signaux", "OS", "Ondes et signaux"),
)
SVT_DOMAINS = (
    ("La Terre, la vie et l’organisation du vivant", "TVOV", "La Terre, la vie et l’organisation du vivant"),
    ("Les enjeux contemporains de la planète", "ECP", "Les enjeux contemporains de la planète"),
    ("Enjeux contemporains de la planète", "ECP", "Enjeux contemporains de la planète"),
    ("Enjeux planétaires contemporains", "EPC", "Enjeux planétaires contemporains"),
    ("Corps humain et santé", "CHS", "Corps humain et santé"),
    ("Le corps humain et la santé", "CHS", "Le corps humain et la santé"),
)
ES1_DOMAINS = (
    ("1 — Une longue histoire de la matière", "MATIERE", "Une longue histoire de la matière"),
    ("2 — Le Soleil, notre source d’énergie", "SOLEIL", "Le Soleil, notre source d’énergie"),
    ("3 — La Terre, un astre singulier", "TERRE", "La Terre, un astre singulier"),
    ("4 — Son, musique et audition", "SON", "Son, musique et audition"),
)
ES2_DOMAINS = (
    ("Thème 1 — Science, climat et société", "CLIMAT", "Science, climat et société"),
    ("Thème 2 — Le futur des énergies", "ENERGIES", "Le futur des énergies"),
    ("Thème 3 — Une histoire du vivant", "VIVANT", "Une histoire du vivant"),
)
PC_HEADERS = ("notionsetcontenus", "capacitésexigibles", "activitésexpérimentalessupportdelaformation")
SVT_HEADERS = ("connaissancescapacités,attitudes",)
ES_HEADERS = ("savoirssavoir-faire",)

SPECS: Tuple[DocSpec, ...] = (
    DocSpec("SRC-2NDE-PC-2019", Subject.PHYSIQUE_CHIMIE, Level.SECONDE, Course.COMMON, "PC/2NDE.json",
            "Programme de physique-chimie de seconde générale et technologique — BO spécial n°1 du 22 janvier 2019",
            3, PC_DOMAINS, "table", 3, "contenu", "capacite", PC_HEADERS),
    DocSpec("SRC-1RE-PC-2019", Subject.PHYSIQUE_CHIMIE, Level.PREMIERE, Course.SPECIALITE, "PC/1RE_SPECIALITE.json",
            "Programme de l'enseignement de spécialité de physique-chimie de première générale — BO spécial n°1 du 22 janvier 2019",
            4, PC_DOMAINS, "table", 3, "contenu", "capacite", PC_HEADERS),
    DocSpec("SRC-TLE-PC-2019", Subject.PHYSIQUE_CHIMIE, Level.TERMINALE, Course.SPECIALITE, "PC/TLE_SPECIALITE.json",
            "Programme de l'enseignement de spécialité de physique-chimie de terminale générale — BO spécial n°8 du 25 juillet 2019",
            4, PC_DOMAINS, "table", 4, "contenu", "capacite", PC_HEADERS),
    DocSpec("SRC-2NDE-SVT-2019", Subject.SVT, Level.SECONDE, Course.COMMON, "SVT/2NDE.json",
            "Programme de sciences de la vie et de la Terre de seconde générale et technologique — BO spécial n°1 du 22 janvier 2019",
            3, SVT_DOMAINS, "svt_blocks", 4, "connaissance", "capacite", ()),
    DocSpec("SRC-1RE-SVT-2019", Subject.SVT, Level.PREMIERE, Course.SPECIALITE, "SVT/1RE_SPECIALITE.json",
            "Programme de l'enseignement de spécialité de SVT de première générale — BO spécial n°1 du 22 janvier 2019",
            4, SVT_DOMAINS, "svt_blocks", 5, "connaissance", "capacite", ()),
    DocSpec("SRC-TLE-SVT-2019", Subject.SVT, Level.TERMINALE, Course.SPECIALITE, "SVT/TLE_SPECIALITE.json",
            "Programme de l'enseignement de spécialité de SVT de terminale générale — BO spécial n°8 du 25 juillet 2019",
            4, SVT_DOMAINS, "table", 6, "connaissance", "capacite", SVT_HEADERS),
    DocSpec("SRC-1RE-ES-2023", Subject.ENSEIGNEMENT_SCIENTIFIQUE, Level.PREMIERE, Course.ENSEIGNEMENT_SCIENTIFIQUE,
            "ES/1RE_ENSEIGNEMENT_SCIENTIFIQUE.json",
            "Programme d'enseignement scientifique de première générale — BO n°25 du 22 juin 2023",
            4, ES1_DOMAINS, "table", 4, "savoir", "savoir-faire", ES_HEADERS),
    DocSpec("SRC-TLE-ES-2023", Subject.ENSEIGNEMENT_SCIENTIFIQUE, Level.TERMINALE, Course.ENSEIGNEMENT_SCIENTIFIQUE,
            "ES/TLE_ENSEIGNEMENT_SCIENTIFIQUE.json",
            "Programme d'enseignement scientifique de terminale générale — BO n°25 du 22 juin 2023",
            4, ES2_DOMAINS, "table", 4, "savoir", "savoir-faire", ES_HEADERS),
)


# --------------------------------------------------------------------------- #
# Géométrie : fragments positionnés → rangées
# --------------------------------------------------------------------------- #
@dataclass
class Frag:
    x: float
    y: float
    text: str
    bold: bool
    size: float


@dataclass
class Row:
    page: int
    y: float
    frags: List[Frag]

    @property
    def text(self) -> str:
        return "".join(f.text for f in self.frags)

    @property
    def x0(self) -> float:
        return self.frags[0].x

    @property
    def bold(self) -> bool:
        for f in self.frags:
            if re.search(r"\w", f.text):
                return f.bold
        return False

    @property
    def size(self) -> float:
        return max((f.size for f in self.frags if re.search(r"\w", f.text)), default=0.0)

    def part(self, lo: float, hi: float) -> Optional["Row"]:
        fr = [f for f in self.frags if lo <= f.x < hi]
        return Row(self.page, self.y, fr) if fr else None


def compact(s: str) -> str:
    return re.sub(r"\s+", "", s)


def key(s: str) -> str:
    """Clé de comparaison des rubriques : minuscules ASCII sans blancs ni ponctuation."""
    s = s.replace("œ", "oe").replace("Œ", "OE").replace("æ", "ae")
    base = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]", "", base)


def is_bullet_frag(f: Frag) -> bool:
    t = f.text.strip()
    return len(t) == 1 and not t.isalnum() and t not in "(«“"


FOOTER_RE = re.compile(r"(Ministère de l'Éducation|education\.gouv\.fr|Bulletin officiel n°|"
                       r"Sciences de la vie et de la Terre, enseignement commun, classe de seconde)")


def page_rows(reader: PdfReader, pno: int) -> List[Row]:
    frags: List[Frag] = []

    def visit(text, cm, tm, fd, fs):  # noqa: ANN001 - signature imposée par pypdf
        if not text or not text.strip():
            return
        x = tm[4] * cm[0] + cm[4]
        y = tm[5] * cm[3] + cm[5]
        font = str((fd or {}).get("/BaseFont", ""))
        frags.append(Frag(x, y, text.replace("\n", " "), "Bold" in font, float(fs) * abs(cm[3] or 1.0)))

    reader.pages[pno - 1].extract_text(visitor_text=visit)
    frags.sort(key=lambda f: (-round(f.y, 1), f.x))
    rows: List[Row] = []
    for f in frags:
        if rows and abs(rows[-1].y - f.y) <= 3.0:
            rows[-1].frags.append(f)
        else:
            rows.append(Row(pno, f.y, [f]))
    # exposants / indices (corps réduit, ordonnée décalée) : rattachés à la rangée la plus proche
    sizes = sorted(f.size for f in frags if re.search(r"\w", f.text)) or [11.0]
    ref = sizes[len(sizes) // 2]
    big = [r for r in rows if r.size > 0.8 * ref or not re.search(r"\w", r.text) and len(r.frags) > 3]
    if big:
        for r in rows:
            if r in big or r.size > 0.8 * ref:
                continue
            near = min(big, key=lambda b: abs(b.y - r.y))
            if abs(near.y - r.y) <= 7:
                near.frags.extend(r.frags)
            else:
                big.append(r)
        rows = sorted(big, key=lambda r: -r.y)
    out: List[Row] = []
    for r in rows:
        r.frags.sort(key=lambda f: f.x)
        t = r.text.strip()
        if not t or FOOTER_RE.search(t) or re.fullmatch(r"[\d\s]+", t):
            continue
        out.append(r)
    return out


def right_column_x(rows: Sequence[Row], lo: float = 150, hi: float = 400) -> Optional[float]:
    """Abscisse de début de la colonne de droite : valeur la plus fréquente parmi les premiers
    fragments situés à droite d'un blanc important dans chaque rangée."""
    c: Counter = Counter()
    for r in rows:
        prev_end = None
        for f in r.frags:
            if lo <= f.x <= hi and (prev_end is None or f.x - prev_end > 0):
                c[round(f.x)] += 1
                break
            prev_end = f.x
    if not c:
        return None
    x, n = c.most_common(1)[0]
    return float(x) if n >= 3 else None


# --------------------------------------------------------------------------- #
# Alignement sur le texte brut (source de vérité du libellé)
# --------------------------------------------------------------------------- #
class PlainPage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.idx: List[int] = [i for i, ch in enumerate(text) if not ch.isspace()]
        self.flat = "".join(text[i] for i in self.idx)

    def find(self, chunk: str, start: int = 0) -> Optional[Tuple[int, int]]:
        c = compact(chunk)
        if not c:
            return None
        pos = self.flat.find(c, start)
        if pos < 0:
            pos = self.flat.find(c)
        if pos < 0:
            return None
        return pos, pos + len(c)

    def verbatim(self, a: int, b: int) -> str:
        return self.text[self.idx[a]: self.idx[b - 1] + 1]


SENT_SPLIT = re.compile(r"(?<=[a-zà-ÿœ0-9)\]»%])\.\s+(?=[A-ZÀ-ÖØ-Þ«Œ])")


ANAPHORA = re.compile(r"^(Ce|Cet|Cette|Ces|Celui|Celle|Ceux|Celles|Cela|Ceci|C’est|C'est|Il|Ils|Elle|Elles|"
                      r"Leur|Leurs|Celui-ci|Celle-ci|Ceux-ci|Celles-ci)\b")
ANAPHORIC_KINDS = ("connaissance", "savoir")


def split_sentences(v: str) -> List[str]:
    out, last = [], 0
    for m in SENT_SPLIT.finditer(v):
        out.append(v[last:m.start() + 1])
        last = m.end()
    out.append(v[last:])
    return [s for s in out if s.strip()]


def terminated(s: str) -> bool:
    return bool(re.search(r"[.!?]\s*$", s.strip()))


# --------------------------------------------------------------------------- #
# Collecte
# --------------------------------------------------------------------------- #
@dataclass
class Skipped:
    page: int
    reason: str
    text: str


@dataclass
class Buffer:
    rows: List[Row] = field(default_factory=list)
    kind: str = ""
    mode: str = "sentences"         # sentences | whole
    bold: Optional[bool] = None
    link: bool = False              # renvoi « ↔ » (liens mathématiques ES) : jamais une notion
    drop_head: bool = False         # suite d'un item commencé sur la page précédente


class Collector:
    def __init__(self, spec: DocSpec) -> None:
        self.spec = spec
        self.b = Builder(spec.source_id, spec.subject, spec.course, SCHOOL_YEAR, spec.program_version)
        self.reader = PdfReader(str(REPO_ROOT / self.b.st.source.local_path))
        self.plain = {p: PlainPage("\n".join(ls)) for p, ls in self.b.lines.items()}
        self.cursor: Dict[int, int] = {}
        self.skipped: List[Skipped] = []
        self.domain: Optional[Tuple[str, str]] = None
        self.l1 = ""
        self.l2 = ""
        self.items: List[Item] = []

    # -- rubriques ----------------------------------------------------------- #
    @property
    def chapter(self) -> str:
        parts = [p for p in (self.l1, self.l2) if p]
        ch = " — ".join(parts) if parts else (self.domain[0] if self.domain else "")
        return ch[:200]

    def match_domain(self, text: str) -> Optional[Tuple[str, str]]:
        k = key(text)
        for prefix, code, label in self.spec.domains:
            if k.startswith(key(prefix)) and len(k) <= len(key(prefix)) + 3:
                return label, code
        return None

    # -- émission ------------------------------------------------------------- #
    def emit(self, buf: Buffer, cut_tail: bool) -> bool:
        """Transforme un bloc de colonne en items. Renvoie True si la fin du bloc est une
        phrase inachevée (elle se poursuit ailleurs : elle est alors écartée)."""
        if not buf.rows:
            return False
        page = buf.rows[0].page
        pp = self.plain[page]
        if buf.link:
            self.skipped.append(Skipped(page, "renvoi_mathematique", clean_line(" ".join(r.text for r in buf.rows))[:120]))
            return False
        # segments contigus dans le texte brut
        runs: List[str] = []
        i = 0
        while i < len(buf.rows):
            j = len(buf.rows)
            found = None
            while j > i:
                chunk = "".join(r.text for r in buf.rows[i:j])
                found = pp.find(chunk, self.cursor.get(page, 0))
                if found:
                    break
                j -= 1
            if not found:
                self.skipped.append(Skipped(page, "absent_du_texte_brut", clean_line(buf.rows[i].text)[:120]))
                i += 1
                continue
            runs.append(pp.verbatim(*found))
            self.cursor[page] = found[1]
            i = j
        pieces: List[str] = []
        for v in runs:
            if buf.mode != "sentences":
                pieces.append(v)
                continue
            sents = split_sentences(v)
            if buf.kind in ANAPHORIC_KINDS:
                # une phrase qui reprend la précédente (« Cette… », « Il… ») reste avec elle
                merged: List[str] = []
                for sent in sents:
                    if merged and ANAPHORA.match(sent.strip()):
                        merged[-1] = merged[-1] + " " + sent
                    else:
                        merged.append(sent)
                sents = merged
            pieces.extend(sents)
        if not pieces:
            return False
        tail_open = not terminated(pieces[-1])
        if buf.drop_head:
            self.skipped.append(Skipped(page, "suite_de_page_precedente", clean_line(pieces[0])[:120]))
            pieces = pieces[1:]
        if cut_tail and tail_open and pieces:
            self.skipped.append(Skipped(page, "suite_sur_page_suivante", clean_line(pieces[-1])[:120]))
            pieces = pieces[:-1]
        for s in pieces:
            self.add_item(s, page, buf.kind, bool(buf.bold))
        return tail_open

    def add_item(self, raw: str, page: int, kind: str, bold: bool) -> None:
        if re.search(r"\w-\s*\n\s*\w", raw):
            self.skipped.append(Skipped(page, "cesure_fin_de_ligne", clean_line(raw)[:120]))
            return
        s = clean_line(raw)
        s = re.sub(r"^[-–•]\s*", "", s)
        if not s or self.domain is None:
            return
        if s.startswith("↔"):
            self.skipped.append(Skipped(page, "renvoi_mathematique", s[:120]))
            return
        if re.search(r"[-\U0001d400-\U0001d7ff]", s):
            self.skipped.append(Skipped(page, "symboles_non_textuels", s[:120]))
            return
        if not re.match(r"(pH\b|[A-ZÀ-ÖØ-Þ«Œ(])", s):
            self.skipped.append(Skipped(page, "fragment_sans_majuscule", s[:120]))
            return
        words = s.split()
        if len(words) < MIN_WORDS or sum(1 for w in words if re.search(r"[A-Za-zÀ-ÿ]{2,}", w)) < 3:
            self.skipped.append(Skipped(page, "trop_court", s))
            return
        if not terminated(s) and not (bold and kind == self.spec.left_kind):
            self.skipped.append(Skipped(page, "phrase_inachevee", s[:120]))
            return
        self.items.append(Item(level=self.spec.level, domain=self.domain[0], domain_code=self.domain[1],
                               chapter=self.chapter or self.domain[0], excerpt=s, page=page, kind=kind,
                               difficulty=self.spec.difficulty))


# --------------------------------------------------------------------------- #
# Tableaux à deux colonnes (PC, SVT terminale, ES)
# --------------------------------------------------------------------------- #
NUM_HEADING = re.compile(r"^\s*\d\s*\.\s*[A-ZÀ-ÖØ-Þ]")
LETTER_HEADING = re.compile(r"^\s*[A-H]\s*\)\s*\S")
ES_CHAPTER = re.compile(r"^\s*\d\s*\.\s*\d\s*—\s*(.+)$")
ES_DOMAIN = re.compile(r"^\s*(Thème\s*)?\d\s*—\s*\S")
STOP_TABLE = ("notionsabordees", "pistespourlamiseenoeuvre", "notionsetudiees", "pistesdemiseenoeuvre", "contenusdisciplinaires",
              "reperespourlenseignement")
STOP_DOC = ("capacitesexperimentales",)
SVT_SKIP_BOTH = ("precisions", "liens", "lien")
SVT_SKIP_LEFT = ("notionsfondamentales", "notionfondamentale", "objectifs")


def body_size(rows: Iterable[Row]) -> float:
    c: Counter = Counter()
    for r in rows:
        for f in r.frags:
            c[round(f.size)] += len(f.text)
    return float(c.most_common(1)[0][0]) if c else 11.0


def full_width(r: Row, boundary: float) -> bool:
    """Ligne de paragraphe qui déborde de la colonne de gauche (hors tableau)."""
    return any(f.x < boundary and f.x + 0.42 * f.size * len(f.text) > boundary + 25 for f in r.frags)


def heading_text(rows: Sequence[Row], plain: Optional[Dict[int, "PlainPage"]] = None) -> str:
    """Libellé d'une rubrique : recopié du texte brut de la page quand il s'y retrouve."""
    if plain and rows:
        pp = plain.get(rows[0].page)
        found = pp.find("".join(r.text for r in rows)) if pp else None
        if found:
            return clean_line(pp.verbatim(*found))
    return clean_line(" ".join(r.text for r in rows))


def parse_table(col: Collector) -> None:
    spec = col.spec
    pages = sorted(col.plain)
    all_rows = {p: page_rows(col.reader, p) for p in pages if p >= spec.first_page}
    body = body_size(r for rs in all_rows.values() for r in rs)
    in_table = False
    skip = [False, False]
    bufs = [Buffer(kind=spec.left_kind), Buffer(kind=spec.right_kind)]
    last_y: List[Optional[float]] = [None, None]
    carry = [False, False]
    pending_heading: List[Row] = []
    pending_type = ""
    is_svt = spec.subject == Subject.SVT
    is_pc = spec.subject == Subject.PHYSIQUE_CHIMIE
    last_header: Optional[Tuple[int, float]] = None

    def flush(c: int, cut_tail: bool = False) -> None:
        tail_open = col.emit(bufs[c], cut_tail)
        carry[c] = cut_tail and tail_open
        bufs[c] = Buffer(kind=spec.left_kind if c == 0 else spec.right_kind)
        last_y[c] = None

    def flush_all() -> None:
        flush(0)
        flush(1)

    def close_heading() -> None:
        nonlocal pending_heading, pending_type
        if not pending_heading:
            return
        t = heading_text(pending_heading, col.plain)
        if pending_type == "l1":
            col.l1, col.l2 = t, ""
        elif pending_type == "l2":
            col.l2 = t
        pending_heading, pending_type = [], ""

    def open_heading(r: Row, typ: str) -> None:
        nonlocal pending_heading, pending_type
        if pending_heading and pending_type == typ and pending_heading[-1].page == r.page \
                and pending_heading[-1].y - r.y < 16:
            pending_heading.append(r)
            return
        close_heading()
        pending_heading, pending_type = [r], typ

    for p in pages:
        if p < spec.first_page:
            continue
        rows = all_rows[p]
        xr = right_column_x(rows)
        boundary = (xr - 6) if xr else 10_000.0
        # changement de page : un item ne franchit jamais une page
        for c in (0, 1):
            if bufs[c].rows:
                flush(c, cut_tail=True)
        for r in rows:
            t = r.text
            k = key(t)
            if any(k.startswith(s) for s in STOP_DOC) and r.size >= body + 2:
                flush_all()
                close_heading()
                return
            # --- rubriques pleine largeur ------------------------------------ #
            dom = col.match_domain(t) if (r.size >= body + 2 or ES_DOMAIN.match(t)) else None
            if dom:
                flush_all()
                close_heading()
                col.domain, col.l1, col.l2 = dom, "", ""
                in_table, skip = False, [False, False]
                continue
            if r.size >= body + 2:
                flush_all()
                close_heading()
                if is_svt:
                    col.l1, col.l2 = "", ""
                in_table = False
                continue
            if spec.subject == Subject.ENSEIGNEMENT_SCIENTIFIQUE and ES_CHAPTER.match(t):
                flush_all()
                open_heading(r, "l1")
                in_table = False
                continue
            if pending_heading and pending_type == "l1" and spec.subject == Subject.ENSEIGNEMENT_SCIENTIFIQUE \
                    and r.bold and r.page == pending_heading[-1].page and pending_heading[-1].y - r.y < 16:
                pending_heading.append(r)
                continue
            if is_pc and r.bold and NUM_HEADING.match(t) and r.x0 < 100:
                flush_all()
                open_heading(r, "l1")
                # le tableau se poursuit souvent sous la rubrique ; un paragraphe pleine largeur
                # (introduction de la partie) le refermera
                in_table = last_header is not None
                continue
            if is_pc and pending_heading and pending_type == "l1" and r.bold and r.x0 < 100 \
                    and r.page == pending_heading[-1].page and pending_heading[-1].y - r.y < 16:
                pending_heading.append(r)
                continue
            if is_pc and LETTER_HEADING.match(t) and r.x0 < 100:
                flush_all()
                open_heading(r, "l2")
                continue
            if is_svt and len(r.frags) >= 2 and is_bullet_frag(r.frags[0]) and r.frags[1].bold and r.x0 < 80:
                flush_all()
                open_heading(Row(r.page, r.y, r.frags[1:]), "l1")
                in_table = False
                continue
            if any(k.startswith(s) for s in STOP_TABLE):
                flush_all()
                close_heading()
                in_table = False
                continue
            if len(compact(t)) < 90 and any(k.startswith(key(h)) or key(h).startswith(k) and len(k) > 8
                                            for h in spec.header_keys):
                flush_all()
                close_heading()
                in_table, skip = True, [False, False]
                last_header = (r.page, r.y)
                continue
            if is_svt and r.bold and any(k.startswith(s) for s in SVT_SKIP_BOTH):
                flush_all()
                skip = [True, True]
                continue
            if not in_table:
                continue
            if is_pc and full_width(r, boundary):
                flush_all()
                close_heading()
                in_table = False
                continue
            if pending_heading and pending_heading[-1].y - r.y > 16:
                close_heading()
            # --- colonnes ----------------------------------------------------- #
            for c, part in ((0, r.part(-1e9, boundary)), (1, r.part(boundary, 1e9))):
                if part is None:
                    continue
                pt = part.text
                pk = key(pt)
                if c == 0 and is_svt and part.bold and not any(pk.startswith(s) for s in SVT_SKIP_LEFT):
                    # intertitre de la colonne « Connaissances »
                    flush(0)
                    skip[0] = False
                    if part.x0 < boundary and part.frags[0].x < 73:
                        if pending_heading and pending_type == "l2" and pending_heading[-1].y - r.y < 16:
                            pending_heading.append(part)
                        else:
                            close_heading()
                            open_heading(part, "l2")
                    else:
                        close_heading()
                    continue
                if c == 0 and is_svt and any(pk.startswith(s) for s in SVT_SKIP_LEFT):
                    flush(0)
                    skip[0] = True
                    continue
                if skip[c]:
                    continue
                buf = bufs[c]
                if pt.strip().startswith("↔"):
                    flush(c)
                    bufs[c].link = True
                    bufs[c].rows.append(part)
                    last_y[c] = r.y
                    continue
                if buf.link:
                    if not terminated(buf.rows[-1].text):
                        # renvoi « ↔ » sur plusieurs lignes : sa suite est écartée avec lui
                        buf.rows.append(part)
                        last_y[c] = r.y
                        continue
                    flush(c)
                    buf = bufs[c]
                gap = (last_y[c] - r.y) if last_y[c] is not None else 0
                if buf.rows and (gap > 21 or (is_pc and c == 0 and buf.bold is not None and buf.bold != part.bold)):
                    flush(c)
                    buf = bufs[c]
                if not buf.rows:
                    buf.bold = part.bold
                    if carry[c]:
                        buf.drop_head = True
                        carry[c] = False
                buf.rows.append(part)
                last_y[c] = r.y
        close_heading()
    for c in (0, 1):
        flush(c)


# --------------------------------------------------------------------------- #
# SVT 2nde / 1re : blocs « Connaissances » / « Capacités » en une colonne
# --------------------------------------------------------------------------- #
def parse_svt_blocks(col: Collector) -> None:
    spec = col.spec
    pages = sorted(col.plain)
    all_rows = {p: page_rows(col.reader, p) for p in pages if p >= spec.first_page}
    body = body_size(r for rs in all_rows.values() for r in rs)
    mode = "skip"
    buf = Buffer()
    last_y: Optional[float] = None
    carry = False
    pending: List[Row] = []
    pending_type = ""

    def flush(cut_tail: bool = False) -> None:
        nonlocal buf, last_y, carry
        tail_open = col.emit(buf, cut_tail)
        carry = cut_tail and tail_open
        buf = Buffer(kind=spec.left_kind if mode == "conn" else spec.right_kind,
                     mode="sentences" if mode == "conn" else "whole")
        last_y = None

    def close_heading() -> None:
        nonlocal pending, pending_type
        if pending:
            t = heading_text(pending, col.plain)
            if pending_type == "l1":
                col.l1, col.l2 = t, ""
            else:
                col.l2 = t
        pending, pending_type = [], ""

    def open_heading(r: Row, typ: str) -> None:
        nonlocal pending, pending_type
        if pending and pending_type == typ and pending[-1].page == r.page and pending[-1].y - r.y < 20:
            pending.append(r)
            return
        close_heading()
        pending, pending_type = [r], typ

    def new_buf() -> Buffer:
        return Buffer(kind=spec.left_kind if mode == "conn" else spec.right_kind,
                      mode="sentences" if mode == "conn" else "whole")

    for p in pages:
        if p < spec.first_page:
            continue
        if buf.rows:
            flush(cut_tail=True)
        for r in all_rows[p]:
            t = r.text
            k = key(t)
            bullet = len(r.frags) >= 2 and is_bullet_frag(r.frags[0]) and r.x0 < 80
            if r.size >= body + 2:
                flush()
                close_heading()
                dom = col.match_domain(t)
                if dom:
                    col.domain, col.l1, col.l2 = dom, "", ""
                elif col.domain and r.size < body + 5 and r.bold:
                    open_heading(r, "l1")
                else:
                    col.l1, col.l2 = "", ""
                mode = "skip"
                continue
            if bullet and r.frags[1].bold and not r.frags[1].text.strip().startswith(("-",)):
                flush()
                open_heading(Row(r.page, r.y, r.frags[1:]), "l1")
                mode = "skip"
                continue
            if r.bold and k in ("connaissances",):
                flush()
                close_heading()
                mode = "conn"
                buf = new_buf()
                continue
            if r.bold and k in ("capacites",):
                flush()
                close_heading()
                mode = "cap"
                buf = new_buf()
                continue
            if r.bold and any(k.startswith(s) for s in SVT_SKIP_LEFT + SVT_SKIP_BOTH + ("pourlensembledutheme",)):
                flush()
                close_heading()
                mode = "skip"
                continue
            if not bullet and (r.x0 >= 112 or (r.bold and r.x0 < 100)):
                flush()
                open_heading(r, "l2")
                mode = "skip"
                continue
            close_heading()
            if mode == "skip":
                continue
            gap = (last_y - r.y) if last_y is not None else 0
            if buf.rows and (gap > 21 or (mode == "cap" and bullet)):
                flush()
            if mode == "cap" and not buf.rows and not bullet:
                # ligne de capacité sans puce : suite d'une puce commencée page précédente
                if carry:
                    col.skipped.append(Skipped(p, "suite_de_page_precedente", clean_line(t)[:120]))
                    last_y = r.y
                    continue
            if not buf.rows and carry:
                buf.drop_head = mode == "conn"
                carry = False
            buf.rows.append(Row(r.page, r.y, r.frags[1:]) if bullet else r)
            last_y = r.y
        close_heading()
    flush()


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def build(spec: DocSpec) -> Tuple[Builder, List[Skipped]]:
    col = Collector(spec)
    (parse_table if spec.layout == "table" else parse_svt_blocks)(col)
    # un intitulé de ligne en gras répété mot pour mot dans la cellule (« X » puis « X. ») : un seul item
    seen: Dict[Tuple[str, str, str], Item] = {}
    kept: List[Item] = []
    for it in col.items:
        k = (it.chapter, it.kind, clean_line(it.excerpt).rstrip(" .").casefold())
        prev = seen.get(k)
        if prev is not None:
            if not terminated(prev.excerpt) and terminated(it.excerpt):
                kept[kept.index(prev)] = it
                seen[k] = it
            col.skipped.append(Skipped(it.page, "doublon_dans_le_chapitre", it.excerpt[:120]))
            continue
        seen[k] = it
        kept.append(it)
    for it in kept:
        col.b.add(it)
    return col.b, col.skipped


def output_path(spec: DocSpec, data_dir: Path = DATA_DIR) -> Path:
    return data_dir / "notions" / spec.out


def main() -> int:
    status = 0
    for spec in SPECS:
        b, skipped = build(spec)
        notions = link_sequential_prerequisites(b.notions)
        write_notion_file(output_path(spec), spec.subject, spec.level, spec.course, notions, GENERATED_BY)
        reasons = Counter(s.reason for s in skipped)
        print(f"{spec.source_id} → {spec.out}: {len(notions)} notions prouvées ; "
              f"{report_rejections(b.rejected, limit=5)} ; écartés à l'analyse : {dict(sorted(reasons.items()))}")
        if b.rejected:
            status = 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())
