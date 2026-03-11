import type { MessageMetadata, RecommendationCard } from './api/queries'

function RecommendationAction({
  href,
  label,
  variant = 'primary',
}: {
  href?: string
  label?: string
  variant?: 'primary' | 'secondary'
}) {
  if (!href || !label) return null

  return (
    <a
      href={href}
      target={href.startsWith('http') ? '_blank' : undefined}
      rel={href.startsWith('http') ? 'noopener noreferrer' : undefined}
      className={`recommendation-action ${variant === 'secondary' ? 'secondary' : ''}`}
    >
      {label}
    </a>
  )
}

function RecommendationCardView({ card }: { card: RecommendationCard }) {
  return (
    <article className={`recommendation-card recommendation-card-${card.kind}`}>
      {card.media_image && (
        <div className="recommendation-media">
          <img src={card.media_image} alt={card.title} />
        </div>
      )}

      <div className="recommendation-body">
        <div className="recommendation-header">
          <p className="recommendation-kicker">{card.kind}</p>
          <h4>{card.title}</h4>
          {card.subtitle && <p className="recommendation-subtitle">{card.subtitle}</p>}
        </div>

        {card.description && <p className="recommendation-description">{card.description}</p>}

        {!!card.badges?.filter(Boolean).length && (
          <div className="recommendation-badges">
            {card.badges.filter(Boolean).map((badge) => (
              <span key={`${card.id}-${badge}`} className="recommendation-badge">
                {badge}
              </span>
            ))}
          </div>
        )}

        <div className="recommendation-actions">
          <RecommendationAction href={card.cta_href} label={card.cta_label} />
          <RecommendationAction href={card.secondary_cta_href} label={card.secondary_cta_label} variant="secondary" />
        </div>
      </div>
    </article>
  )
}

export default function RecommendationCards({ metadata }: { metadata?: MessageMetadata }) {
  const cards = metadata?.cards ?? []
  if (metadata?.ui_type !== 'recommendations' || cards.length === 0) return null

  return (
    <div className={`recommendation-stack recommendation-stack-${metadata.recommendation_kind ?? 'generic'}`}>
      {cards.map((card) => (
        <RecommendationCardView key={card.id} card={card} />
      ))}
    </div>
  )
}
