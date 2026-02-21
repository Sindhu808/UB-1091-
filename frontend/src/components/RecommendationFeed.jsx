/**
 * RecommendationFeed – displays live AI recommendations with priority badges
 */

const ACTION_ICONS = {
    CHARGE: '⚡',
    DISCHARGE: '🔋',
    CURTAIL: '✂️',
    SHIFT_LOAD: '🕐',
    IMPORT: '🔌',
    OPTIMAL: '✅',
}

export default function RecommendationFeed({ recommendations = [] }) {
    if (!recommendations.length) {
        return (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem', padding: '12px 0' }}>
                Waiting for recommendations…
            </div>
        )
    }

    return (
        <div className="rec-feed">
            {recommendations.map((rec, i) => (
                <div key={i} className="rec-item">
                    <div>
                        <span className={`rec-badge ${rec.priority}`}>
                            {ACTION_ICONS[rec.action] || '●'} {rec.priority}
                        </span>
                    </div>
                    <div>
                        <div className="rec-text">{rec.message}</div>
                        <div className="rec-reason">{rec.reason}</div>
                    </div>
                </div>
            ))}
        </div>
    )
}
