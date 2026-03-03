"""
KnowledgeScanner — BM25-ranked retrieval of financial regulations and
bias definitions.

Purpose
-------
Prevent LLM hallucination of precise financial/regulatory definitions by
providing a grounded, exact-match retrieval layer.  Before any LLM call
that touches compliance language or bias terminology, nodes should call
``scanner.augment_prompt(query)`` to inject verified definitions into the
system or user content.

Architecture
------------
BM25 (Best Match 25, Okapi variant) is a probabilistic keyword-ranking
algorithm that scores documents by term frequency weighted against
inverse-document frequency.  Unlike vector search it is:

  • Exact-match biased — "MAS Notice SFA04-N14" scores higher than a
    semantically similar but terminologically different passage.
  • Deterministic — same query always returns the same ranked list.
  • Zero-latency — no embedding model or network call required.
  • Hallucination-resistant — definitions come from the curated corpus,
    not from model weights.

Vector search (pgvector in hub.knowledge_base) is the complementary layer
for semantic / conceptual retrieval.  Use BM25 for terms, pgvector for
concepts.

Corpus structure
----------------
Documents are tagged by category:
  • "regulation"  — MAS notices, acts, guidelines
  • "calculation" — return metrics, alpha, risk ratios
  • "bias"        — behavioural finance bias definitions
  • "term"        — general financial terminology

Usage
-----
    from graph.knowledge_scanner import scanner

    # In a LangGraph node, before calling the LLM:
    context = scanner.augment_prompt("MAS compliance suitability obligation")
    # Inject `context` into the system prompt or user turn.

    # Direct search:
    results = scanner.search("disposition effect Shefrin", k=2)
    for r in results:
        print(r.score, r.doc.title)
"""

import math
import re
from dataclasses import dataclass, field


# ── Document model ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class KnowledgeDoc:
    id: str
    title: str
    content: str
    category: str          # "regulation" | "calculation" | "bias" | "term"
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class KnowledgeResult:
    doc: KnowledgeDoc
    score: float


# ── Corpus ────────────────────────────────────────────────────────────────────
# Each entry is a concise but precise definition drawn from authoritative sources.
# Extend this list as new regulatory guidance is published or new biases are
# added to the Neufin taxonomy.

_CORPUS: list[KnowledgeDoc] = [

    # ── MAS Regulations ──────────────────────────────────────────────────────

    KnowledgeDoc(
        id="mas-sfa04-n14",
        title="MAS Notice SFA04-N14 — Personal Account Dealing",
        category="regulation",
        tags=("MAS", "SFA", "compliance", "personal account"),
        content=(
            "MAS Notice SFA04-N14 requires capital markets intermediaries to "
            "establish written policies governing personal account dealing by "
            "representatives. Policies must address pre-clearance of trades in "
            "securities the firm has a pending order in, a minimum holding period "
            "(typically 30 days), and prohibition on front-running client orders. "
            "Breaches are reportable events under the Securities and Futures Act "
            "(SFA, Cap. 289) and may constitute market misconduct under Part XII."
        ),
    ),

    KnowledgeDoc(
        id="mas-faa-suitability",
        title="MAS FAA — Suitability Obligation (Section 27)",
        category="regulation",
        tags=("MAS", "FAA", "suitability", "compliance", "financial adviser"),
        content=(
            "Under Section 27 of the Financial Advisers Act (FAA, Cap. 110), a "
            "financial adviser must have a reasonable basis for any recommendation "
            "having regard to the customer's financial objectives, risk tolerance, "
            "investment horizon, and existing portfolio. The adviser must document "
            "the basis of the recommendation. The MAS Suitability Framework (2012) "
            "operationalises this obligation: advisers must obtain a Customer "
            "Knowledge Assessment (CKA) or Customer Account Review (CAR) before "
            "recommending Specified Investment Products (SIPs). Unsolicited "
            "transactions in SIPs require the client to acknowledge the absence of "
            "an advisory relationship."
        ),
    ),

    KnowledgeDoc(
        id="mas-sfa-false-trading",
        title="MAS SFA Part XII — False Trading and Market Manipulation",
        category="regulation",
        tags=("MAS", "SFA", "market manipulation", "false trading", "compliance"),
        content=(
            "Part XII of the Securities and Futures Act prohibits false trading "
            "(Section 197), market manipulation (Section 198), and dissemination "
            "of false or misleading information (Section 200). False trading occurs "
            "when a person creates, or is likely to create, a false or misleading "
            "appearance of active trading or the price of securities. Penalties "
            "include civil penalty of up to SGD 2 million or three times the profit "
            "gained. Criminal conviction carries up to 7 years' imprisonment. "
            "MAS may also issue prohibition orders under Section 101A of the FAA."
        ),
    ),

    KnowledgeDoc(
        id="mas-cm-s3-retail-classification",
        title="MAS CM-S3 — Retail and Accredited Investor Classification",
        category="regulation",
        tags=("MAS", "accredited investor", "retail client", "classification", "compliance"),
        content=(
            "MAS CM-S3 (Guidelines on Criteria for the Grant of a Capital Markets "
            "Services Licence) and accompanying SFA regulations define Retail Clients "
            "as individuals who do not qualify as Accredited Investors (AI). An AI "
            "is an individual whose net personal assets exceed SGD 2 million (with "
            "primary residence capped at SGD 1 million), or whose income in the "
            "preceding 12 months is not less than SGD 300,000. Institutional "
            "Investors include licensed banks, insurers, and fund managers. "
            "Client classification determines product access: certain leveraged "
            "and complex instruments are restricted to AI/Institutional Investors."
        ),
    ),

    KnowledgeDoc(
        id="mas-faa-n16-disclosure",
        title="MAS Notice FAA-N16 — Disclosure and Product Recommendation Basis",
        category="regulation",
        tags=("MAS", "FAA", "disclosure", "product recommendation", "KYC"),
        content=(
            "MAS Notice FAA-N16 mandates that a financial adviser disclose: (a) all "
            "material conflicts of interest, (b) the basis of any recommendation "
            "including the specific customer information relied upon, (c) all "
            "material risks of the recommended product, and (d) whether the adviser "
            "is selling a house product. The notice requires advisers to provide a "
            "Product Summary and a Benefit Illustration where applicable. Failure to "
            "disclose constitutes a breach of the FAA and may attract regulatory "
            "sanctions including licence revocation."
        ),
    ),

    KnowledgeDoc(
        id="mas-trm-guidelines",
        title="MAS TRM Guidelines 2021 — Technology Risk Management",
        category="regulation",
        tags=("MAS", "technology risk", "TRM", "cyber security", "compliance"),
        content=(
            "The MAS Technology Risk Management Guidelines (revised 2021) set "
            "principles for financial institutions to manage technology risks. Key "
            "requirements include: establishing a board-level technology risk "
            "appetite, maintaining a Technology Risk Management Framework, conducting "
            "annual penetration testing for internet-facing systems, and achieving "
            "recovery time objectives of no more than 4 hours for critical systems. "
            "AI and algorithmic trading systems must be subject to model risk "
            "management including validation, stress testing, and explainability "
            "requirements before deployment."
        ),
    ),

    KnowledgeDoc(
        id="mas-conduct-risk",
        title="MAS Conduct Risk — Thematic Review Definition",
        category="regulation",
        tags=("MAS", "conduct risk", "fair dealing", "compliance"),
        content=(
            "MAS defines Conduct Risk as the risk that the behaviour of a financial "
            "institution or its representatives leads to poor outcomes for customers, "
            "market integrity, or the firm itself. The MAS Fair Dealing Guidelines "
            "(2009, updated 2013) require boards to embed five fair dealing outcomes: "
            "(1) customers receive fair dealing; (2) products and services are "
            "suitable; (3) pre-sale disclosures are adequate; (4) advice is "
            "independent and fair; (5) complaints are handled promptly. Behavioural "
            "biases in representatives that systematically disadvantage clients "
            "constitute conduct risk."
        ),
    ),

    # ── Return / Alpha Calculations ───────────────────────────────────────────

    KnowledgeDoc(
        id="calc-jensens-alpha",
        title="Jensen's Alpha — Abnormal Return vs CAPM Benchmark",
        category="calculation",
        tags=("alpha", "CAPM", "Jensen", "abnormal return", "benchmark"),
        content=(
            "Jensen's Alpha (α) measures the excess return of a portfolio or security "
            "above what CAPM predicts given its systematic risk. "
            "Formula: α = Rp − [Rf + βp × (Rm − Rf)] "
            "where Rp = portfolio return, Rf = risk-free rate (e.g. 3-month T-bill), "
            "βp = portfolio beta (sensitivity to market), Rm = market return. "
            "A positive alpha indicates outperformance after adjusting for risk. "
            "Alpha Leak: the portion of alpha that is foregone due to behavioural "
            "trading errors such as premature selling, overtrading, or FOMO entry "
            "at suboptimal prices. Alpha Leak = α_potential − α_realised."
        ),
    ),

    KnowledgeDoc(
        id="calc-information-ratio",
        title="Information Ratio — Active Return per Unit of Tracking Error",
        category="calculation",
        tags=("information ratio", "IR", "active return", "tracking error", "alpha"),
        content=(
            "Information Ratio (IR) = (Rp − Rb) / σ(Rp − Rb) "
            "where Rp = portfolio return, Rb = benchmark return, "
            "σ(Rp − Rb) = tracking error (standard deviation of excess returns). "
            "IR measures the consistency and magnitude of active management skill. "
            "IR > 0.5 is generally considered skilled; IR > 1.0 is exceptional. "
            "Behavioural biases reduce IR by introducing idiosyncratic timing errors: "
            "FOMO entry raises the average cost basis, reducing Rp − Rb, while "
            "the disposition effect increases tracking error through inconsistent "
            "realisation of gains and losses."
        ),
    ),

    KnowledgeDoc(
        id="calc-sharpe-ratio",
        title="Sharpe Ratio — Risk-Adjusted Return",
        category="calculation",
        tags=("Sharpe", "risk-adjusted return", "volatility", "Rf"),
        content=(
            "Sharpe Ratio = (Rp − Rf) / σp "
            "where σp is the annualised standard deviation of portfolio returns. "
            "Developed by William Sharpe (1966). A Sharpe Ratio > 1.0 indicates "
            "the portfolio earns more than one unit of return per unit of risk. "
            "Behavioural drag: overtrading (driven by overconfidence or FOMO) "
            "raises transaction costs and realised volatility, reducing σp's "
            "denominator efficiency. Sunk cost behaviour increases drawdown depth, "
            "further reducing the ratio."
        ),
    ),

    KnowledgeDoc(
        id="calc-sortino-ratio",
        title="Sortino Ratio — Downside Risk-Adjusted Return",
        category="calculation",
        tags=("Sortino", "downside deviation", "MAR", "downside risk"),
        content=(
            "Sortino Ratio = (Rp − MAR) / σd "
            "where MAR = Minimum Acceptable Return and σd = downside deviation "
            "(standard deviation of returns below MAR only). Unlike the Sharpe "
            "Ratio, Sortino does not penalise upside volatility. Particularly "
            "relevant for Neufin because the disposition effect disproportionately "
            "increases downside deviation: holding losers increases the frequency "
            "and magnitude of returns below MAR, reducing the Sortino Ratio even "
            "when the Sharpe Ratio appears acceptable."
        ),
    ),

    KnowledgeDoc(
        id="calc-max-drawdown",
        title="Maximum Drawdown — Peak-to-Trough Loss",
        category="calculation",
        tags=("maximum drawdown", "MDD", "drawdown", "risk", "peak trough"),
        content=(
            "Maximum Drawdown (MDD) = (Trough Value − Peak Value) / Peak Value × 100% "
            "Measures the largest peak-to-trough decline in portfolio value over a "
            "specified period before a new peak is achieved. MDD is highly sensitive "
            "to sunk cost behaviour: refusing to close a losing position extends the "
            "trough duration, deepening the MDD. Recovery time from MDD increases "
            "geometrically with the drawdown size (a 50% loss requires a 100% gain "
            "to recover). MDD is a key risk metric used by MAS in assessing the "
            "risk management adequacy of discretionary fund managers."
        ),
    ),

    KnowledgeDoc(
        id="calc-alpha-leak",
        title="Alpha Leak — Return Foregone Due to Behavioural Bias",
        category="calculation",
        tags=("alpha leak", "behavioural drag", "cognitive bias", "alpha", "performance"),
        content=(
            "Alpha Leak quantifies the return a portfolio sacrifices due to "
            "systematically suboptimal trade timing caused by cognitive biases. "
            "Calculation: Alpha Leak (bps/year) = α_theoretical − α_realised, "
            "where α_theoretical is estimated using a factor model assuming "
            "emotionally neutral execution, and α_realised is the observed alpha. "
            "Empirical studies (Odean 1999, Barber & Odean 2000) document that "
            "retail investors underperform market benchmarks by 1.5–3.7% annually "
            "primarily due to overtrading and the disposition effect. "
            "At Neufin, historical_alpha_leak in UserBehaviorProfile represents "
            "this estimate in percentage points per annum."
        ),
    ),

    # ── Bias Definitions ─────────────────────────────────────────────────────

    KnowledgeDoc(
        id="bias-fomo",
        title="FOMO — Fear Of Missing Out",
        category="bias",
        tags=("FOMO", "fear of missing out", "momentum", "herding", "behavioural bias"),
        content=(
            "FOMO (Fear Of Missing Out) in financial markets describes the emotional "
            "impulse to enter a position driven by the fear of being excluded from "
            "gains witnessed by peers or reported in media, rather than by "
            "fundamental analysis. FOMO-driven trades typically occur after a "
            "significant price run-up, carry above-average sentiment scores (> +0.5 "
            "on the Neufin scale), and are often accompanied by high news volume. "
            "Academic grounding: a form of herding behaviour (Banerjee 1992) and "
            "regret theory (Loomes & Sugden 1982). Cost: FOMO trades systematically "
            "buy near local highs, increasing average cost basis and reducing "
            "alpha by 0.4–1.2% annually (Statman 2004)."
        ),
    ),

    KnowledgeDoc(
        id="bias-disposition-effect",
        title="Disposition Effect — Selling Winners, Holding Losers",
        category="bias",
        tags=("disposition effect", "loss aversion", "Shefrin", "Statman", "behavioural bias"),
        content=(
            "The Disposition Effect (Shefrin & Statman 1985) is the empirically "
            "documented tendency of investors to sell assets that have risen in "
            "value (winners) while holding assets that have fallen in value "
            "(losers). Mechanism: rooted in prospect theory (Kahneman & Tversky "
            "1979) — the S-shaped value function means investors are risk-averse "
            "in the gain domain (lock in profits early) and risk-seeking in the "
            "loss domain (gamble on recovery). In Neufin's taxonomy this manifests "
            "as: multiple losing trades in the same asset held beyond the "
            "trader's stated stop-loss, alongside early exits on profitable "
            "positions. Cost: Odean (1998) demonstrates a 3.4% annual performance "
            "gap between winners sold and losers retained."
        ),
    ),

    KnowledgeDoc(
        id="bias-sunk-cost",
        title="Sunk Cost Fallacy — Doubling Down on Committed Capital",
        category="bias",
        tags=("sunk cost", "sunk cost fallacy", "averaging down", "Arkes", "Blumer"),
        content=(
            "The Sunk Cost Fallacy (Arkes & Blumer 1985) occurs when a decision-maker "
            "continues an endeavour based on previously invested resources (time, "
            "money) that cannot be recovered, rather than on the prospective merit "
            "of continuing. In trading, this manifests as averaging down into a "
            "declining position solely because of prior capital committed — 'I've "
            "already lost 20%, I can't sell now.' Distinguishing feature: the trader "
            "explicitly references their entry price or prior loss as the reason "
            "to maintain or add to a position, rather than citing new information "
            "or improved outlook. Rational decision-making requires treating sunk "
            "costs as irrelevant to forward-looking analysis."
        ),
    ),

    KnowledgeDoc(
        id="bias-loss-aversion",
        title="Loss Aversion — Asymmetric Sensitivity to Gains vs Losses",
        category="bias",
        tags=("loss aversion", "prospect theory", "Kahneman", "Tversky", "behavioural bias"),
        content=(
            "Loss Aversion (Kahneman & Tversky 1979, Prospect Theory) describes the "
            "empirical finding that losses loom approximately 2–2.5 times larger "
            "psychologically than equivalent gains. In trading: a trader experiencing "
            "loss aversion will exit winners too early (to lock in the positive "
            "feeling) and hold losers too long (to avoid crystallising the painful "
            "loss). Distinguished from the disposition effect in that loss aversion "
            "is the underlying psychological mechanism, while the disposition effect "
            "is the observable behavioural outcome. Sentiment scores below −0.3 on "
            "profitable exits or above +0.3 on losing entries are indicative."
        ),
    ),

    KnowledgeDoc(
        id="bias-overconfidence",
        title="Overconfidence — Overestimating Skill Relative to Luck",
        category="bias",
        tags=("overconfidence", "calibration", "excessive trading", "behavioural bias"),
        content=(
            "Overconfidence in investing manifests as: (1) calibration overconfidence "
            "— confidence intervals around price targets are too narrow; (2) above- "
            "average effect — traders believe their skill exceeds the median; "
            "(3) illusion of control — traders attribute random outcomes to personal "
            "skill. Observable signals: excessive trade frequency uncorrelated with "
            "information arrival, large position sizes inconsistent with historical "
            "hit rate, and positive sentiment scores before trades that subsequently "
            "move adversely. Barber & Odean (2001) demonstrate that the most active "
            "traders underperform the least active by 6.5% annually after costs."
        ),
    ),

    KnowledgeDoc(
        id="bias-recency-bias",
        title="Recency Bias — Over-weighting Recent Price Movements",
        category="bias",
        tags=("recency bias", "availability heuristic", "momentum", "behavioural bias"),
        content=(
            "Recency Bias (a manifestation of the Availability Heuristic, Tversky & "
            "Kahneman 1973) causes investors to over-weight recent price movements "
            "when forming expectations about future performance. In practice: a "
            "trader who has observed three consecutive up-days in an asset assigns "
            "a higher probability to a fourth up-day than base rates justify. In "
            "Neufin: sentiment scores correlate positively with trailing 5-day "
            "returns in the asset. The bias amplifies FOMO entries and delays "
            "exits from assets exhibiting negative momentum."
        ),
    ),

    KnowledgeDoc(
        id="bias-anchoring",
        title="Anchoring — Reference Point Distortion in Price Decisions",
        category="bias",
        tags=("anchoring", "reference point", "52-week high", "behavioural bias"),
        content=(
            "Anchoring (Tversky & Kahneman 1974) is the tendency to rely "
            "disproportionately on an initial piece of information (the 'anchor') "
            "when making decisions. In trading: the 52-week high or the trader's "
            "own entry price serves as an anchor that distorts target prices and "
            "stop-loss decisions. A trader anchored to a prior high of $200 may "
            "refuse to sell at $150 even when fundamentals justify the price, "
            "expecting 'a return to the anchor.' In Neufin, anchoring is evidenced "
            "by stop-loss thresholds set as fixed percentages from entry price "
            "regardless of asset volatility."
        ),
    ),

    # ── General Financial Terms ───────────────────────────────────────────────

    KnowledgeDoc(
        id="term-wealth-manager",
        title="Wealth Manager — Fiduciary Role and Regulatory Obligations",
        category="term",
        tags=("wealth manager", "fiduciary", "HNW", "advisory", "MAS"),
        content=(
            "A Wealth Manager provides holistic financial planning, investment "
            "advisory, and portfolio management services to High Net Worth (HNW) "
            "clients, typically those with investable assets exceeding USD 1 million. "
            "Under MAS regulation (FAA), wealth managers who provide advice on "
            "investments must hold a Capital Markets Services (CMS) licence or "
            "be representatives of a licensed entity. They owe fiduciary duties "
            "including the duty of loyalty (acting in the client's best interest), "
            "duty of care (suitability), and duty of disclosure. "
            "Coach Notes from Neufin's bias detection system are advisory tools "
            "to help wealth managers fulfill their MAS conduct risk obligations."
        ),
    ),

    KnowledgeDoc(
        id="term-volatility-regime",
        title="Volatility Regime — Market Condition Classification",
        category="term",
        tags=("volatility", "VIX", "regime", "risk", "market condition"),
        content=(
            "A Volatility Regime describes the prevailing level of market uncertainty "
            "as measured by implied volatility (e.g. VIX for US equities, VHSI for "
            "Hong Kong). Regimes: Low (<15 VIX), Normal (15–25), Elevated (25–35), "
            "Crisis (>35). In Neufin's bias analysis, a high sentiment score "
            "(>+0.5) during an elevated or crisis volatility regime is a strong "
            "indicator of FOMO — the trader is buying into fear-driven volatility "
            "rather than making a calm, analytical decision. Conversely, a negative "
            "sentiment score during a low-volatility regime may indicate "
            "confirmation bias or anchoring."
        ),
    ),
]


# ── BM25 implementation (no external library required) ───────────────────────
# We implement a lightweight BM25-Okapi scorer inline to keep shared_services
# free of additional mandatory dependencies.  Add `rank-bm25` to requirements
# and swap the implementation if corpus size exceeds ~10 000 documents.

_STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "shall", "that", "this",
        "these", "those", "it", "its", "not", "also", "such", "where", "which",
    }
)


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, remove stopwords."""
    tokens = re.findall(r"[a-z0-9]+(?:[._\-][a-z0-9]+)*", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


class _BM25Okapi:
    """
    Minimal BM25-Okapi implementation.

    k1 = 1.5  (term frequency saturation)
    b  = 0.75 (length normalisation)
    """

    _K1 = 1.5
    _B = 0.75

    def __init__(self, tokenized_corpus: list[list[str]]) -> None:
        self._n = len(tokenized_corpus)
        self._avgdl = (
            sum(len(d) for d in tokenized_corpus) / self._n if self._n else 1
        )
        # Term → document frequency
        self._df: dict[str, int] = {}
        # Per-document term frequency
        self._tf: list[dict[str, int]] = []
        self._dl: list[int] = []
        for doc in tokenized_corpus:
            self._dl.append(len(doc))
            tf: dict[str, int] = {}
            for token in doc:
                tf[token] = tf.get(token, 0) + 1
            self._tf.append(tf)
            for token in set(doc):
                self._df[token] = self._df.get(token, 0) + 1

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        scores = [0.0] * self._n
        for token in query_tokens:
            if token not in self._df:
                continue
            idf = math.log(
                (self._n - self._df[token] + 0.5) / (self._df[token] + 0.5) + 1
            )
            for i, tf in enumerate(self._tf):
                if token not in tf:
                    continue
                tf_val = tf[token]
                dl = self._dl[i]
                numerator = tf_val * (self._K1 + 1)
                denominator = tf_val + self._K1 * (
                    1 - self._B + self._B * dl / self._avgdl
                )
                scores[i] += idf * numerator / denominator
        return scores


# ── KnowledgeScanner ──────────────────────────────────────────────────────────

class KnowledgeScanner:
    """
    BM25-ranked retrieval over the financial knowledge corpus.

    Instantiated once at module level as ``scanner`` — import and use directly.

    Methods
    -------
    search(query, k=3) → list[KnowledgeResult]
        Return the top-k documents ranked by BM25 score.
    augment_prompt(query, k=3) → str
        Return a formatted context block ready for injection into an LLM
        system prompt or user turn.  Returns empty string if no documents
        score above zero.
    """

    def __init__(self, corpus: list[KnowledgeDoc] = _CORPUS) -> None:
        self._docs = corpus
        tokenized = [
            _tokenize(f"{doc.title} {doc.content} {' '.join(doc.tags)}")
            for doc in corpus
        ]
        self._bm25 = _BM25Okapi(tokenized)

    def search(self, query: str, k: int = 3) -> list[KnowledgeResult]:
        """
        Return up to *k* documents ranked by BM25 relevance to *query*.
        Documents with score == 0 are excluded.
        """
        tokens = _tokenize(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            enumerate(scores), key=lambda x: x[1], reverse=True
        )[:k]
        return [
            KnowledgeResult(doc=self._docs[i], score=s)
            for i, s in ranked
            if s > 0
        ]

    def augment_prompt(self, query: str, k: int = 3) -> str:
        """
        Return a formatted context block for LLM injection.

        Inject the returned string into the system prompt or prepend it to
        the user turn before calling the LLM.  This grounds the model's
        response in verified definitions and prevents hallucination of
        regulatory terms, calculation formulas, or bias definitions.

        Returns empty string when no relevant documents are found.
        """
        results = self.search(query, k=k)
        if not results:
            return ""
        parts = ["## Verified Reference Definitions (do not contradict)\n"]
        for r in results:
            parts.append(f"### {r.doc.title}\n{r.doc.content}\n")
        return "\n".join(parts)


# Module-level singleton — import this directly in graph nodes.
scanner = KnowledgeScanner()
