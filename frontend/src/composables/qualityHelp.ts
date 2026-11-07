/**
 * What each figure of the quality says, in a few simple words: shown beside the figure (see `QualityBlocks`) and all
 * together, with an example, where the quality is looked at (see `QualityHelp`). One place to correct them: they say how
 * `backend/app/services/metrics.py` counts.
 */
export type MetricKey = 'precision' | 'recall' | 'f1' | 'exact' | 'correct' | 'wrong' | 'missed' | 'pending' | 'decisions' | 'confidence'

export interface MetricHelp {
  term: string
  /** What it answers, as a question. */
  question: string
  /** How it is made and what to make of it. */
  text: string
}

export const METRICS: Record<MetricKey, MetricHelp> = {
  precision: {
    term: 'Précision',
    question: 'Quand l’analyse propose quelque chose, a-t-elle raison ?',
    text: 'C’est la part de ses prédictions que vous avez jugées justes : justes ÷ (justes + fausses). Celles que vous n’avez pas encore regardées ne comptent pas. Haute, elle se trompe peu ; basse, elle fait beaucoup de fausses alertes.',
  },
  recall: {
    term: 'Rappel',
    question: 'L’analyse trouve-t-elle tout ce qu’il y avait à trouver ?',
    text: 'C’est la part de ce qui existait qu’elle a trouvé : justes ÷ (justes + manquées). Haut, elle oublie peu ; bas, elle laisse passer beaucoup de choses.',
  },
  f1: {
    term: 'F1',
    question: 'Quelle note d’ensemble, entre précision et rappel ?',
    text: 'Une seule note qui mêle la précision et le rappel (leur moyenne « harmonique »). Elle n’est haute que si les deux le sont : une analyse qui trouve tout mais se trompe souvent, ou qui ne se trompe jamais mais oublie presque tout, a un F1 bas.',
  },
  exact: {
    term: 'Page du modèle exacte',
    question: 'Quand la page est bien reconnue, est-ce la bonne page du modèle ?',
    text: 'Parmi les pages dont l’analyse a trouvé le bon modèle, la part dont elle a aussi trouvé la bonne page de ce modèle (la page 2 d’un formulaire de 3 pages, par exemple).',
  },
  correct: {
    term: 'Justes',
    question: 'Combien de prédictions étaient bonnes ?',
    text: 'Les prédictions que vous avez validées, ou que vous avez corrigées vers le même modèle.',
  },
  wrong: {
    term: 'Fausses',
    question: 'Combien de prédictions étaient mauvaises ?',
    text: 'Les prédictions que vous avez invalidées, ou corrigées vers un autre modèle.',
  },
  missed: {
    term: 'Manquées',
    question: 'Combien de choses l’analyse n’a-t-elle pas vues ?',
    text: 'Ce qu’elle n’a pas trouvé : un élément que vous avez ajouté à la main, ou une prédiction que vous avez corrigée vers un autre modèle (elle compte alors une fois fausse, pour le modèle prédit, et une fois manquée, pour le bon).',
  },
  pending: {
    term: 'En attente',
    question: 'Combien de prédictions restent à regarder ?',
    text: 'Les prédictions que vous n’avez ni validées, ni invalidées, ni corrigées. Elles ne comptent pas dans la précision : plus vous en regardez, plus les chiffres sont fiables.',
  },
  decisions: {
    term: 'Décisions',
    question: 'Sur combien de prédictions les chiffres reposent-ils ?',
    text: 'Le nombre de prédictions que vous avez jugées (justes + fausses). Avec peu de décisions, un pourcentage ne dit pas grand-chose.',
  },
  confidence: {
    term: 'Confiance moyenne',
    question: 'L’analyse est-elle plus sûre d’elle quand elle a raison ?',
    text: 'Le degré de certitude que l’analyse annonçait, en moyenne, quand elle avait raison et quand elle avait tort. Une bonne analyse est nettement plus sûre d’elle quand elle a raison : sinon sa confiance ne veut pas dire grand-chose.',
  },
}

/** The terms in the order they are explained: the three ratios, the page, then the counts. */
export const ORDER: MetricKey[] = ['precision', 'recall', 'f1', 'exact', 'correct', 'wrong', 'missed', 'pending', 'decisions', 'confidence']

/** A made-up case that shows how the ratios are made, with the same formulas as the backend's. */
export const EXAMPLE = { proposed: 10, validated: 8, invalidated: 2, added: 4 }

const percent = (value: number) => `${Math.round(value * 100)} %`

export function exampleFigures() {
  const { validated, invalidated, added } = EXAMPLE
  const precision = validated / (validated + invalidated)
  const recall = validated / (validated + added)
  const f1 = (2 * precision * recall) / (precision + recall)
  return { precision: percent(precision), recall: percent(recall), f1: percent(f1) }
}
