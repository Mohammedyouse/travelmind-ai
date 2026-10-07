import React from 'react'
import type { NotificationItem } from '../services/api'

type NotificationsModalProps = {
    notifications: NotificationItem[]
    onMarkRead: (id: string) => Promise<void>
    onClose: () => void
}

export function NotificationsModal({ notifications, onMarkRead, onClose }: NotificationsModalProps) {
    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div className="modal-dialog notif-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <div>
                        <h3>Notifications & Travel Alerts</h3>
                        <small className="muted-text">{notifications.length} total notifications</small>
                    </div>
                    <button className="close-btn" onClick={onClose}>&times;</button>
                </div>

                <div className="modal-body notif-modal-body">
                    {notifications.length === 0 ? (
                        <p className="empty-copy">No notifications at this time.</p>
                    ) : (
                        <div className="notif-feed">
                            {notifications.map(n => (
                                <div key={n.id} className={`notif-card-item ${n.status === 'unread' ? 'unread-glow' : ''}`}>
                                    <div className="notif-top-line">
                                        <strong className="notif-title-text">{n.title}</strong>
                                        {n.status === 'unread' && (
                                            <button className="mark-read-btn" onClick={() => onMarkRead(n.id)}>
                                                Mark read
                                            </button>
                                        )}
                                    </div>
                                    <p className="notif-message-text">{n.message}</p>
                                    <small className="notif-date-stamp">
                                        {new Date(n.created_at).toLocaleString()}
                                    </small>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
