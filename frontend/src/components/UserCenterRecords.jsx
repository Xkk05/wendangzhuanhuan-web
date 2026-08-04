import { useCallback, useMemo, useState } from 'react';
import { AuthService } from '../services/auth';

const ALL_RECORD_LIMIT = 200;

function normalizeRecordStatus(status) {
  const normalized = String(status || '').toLowerCase();
  if (normalized === 'completed' || normalized === 'success' || normalized === 'done') {
    return 'completed';
  }
  if (normalized === 'failed' || normalized === 'error') {
    return 'failed';
  }
  if (normalized === 'processing' || normalized === 'running') {
    return 'processing';
  }
  if (normalized === 'waiting' || normalized === 'pending' || normalized === 'queued') {
    return 'waiting';
  }
  return normalized || 'unknown';
}

function formatRecordStatus(status, t) {
  const normalized = normalizeRecordStatus(status);
  if (normalized === 'completed') return t('userCenter.record_status_completed');
  if (normalized === 'failed') return t('userCenter.record_status_failed');
  if (normalized === 'processing') return t('userCenter.record_status_processing');
  if (normalized === 'waiting') return t('userCenter.record_status_waiting');
  return status || '--';
}

function formatFileSize(size) {
  const numericSize = Number(size);
  if (!Number.isFinite(numericSize) || numericSize <= 0) {
    return '';
  }

  const units = ['B', 'KB', 'MB', 'GB'];
  let value = numericSize;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  const decimals = value >= 10 || unitIndex === 0 ? 0 : 1;
  return `${value.toFixed(decimals)} ${units[unitIndex]}`;
}

function getRecordKey(record, index) {
  return record.id || [
    record.fileName,
    record.sourceFormat,
    record.targetFormat,
    record.completedAt,
    record.createdAt,
    index,
  ].filter(Boolean).join('-');
}

function UserCenterRecords({ recentRecords = [], token, t, formatDateTime }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [allRecords, setAllRecords] = useState(null);
  const [isLoadingAll, setIsLoadingAll] = useState(false);
  const [loadError, setLoadError] = useState('');

  const recordsToShow = useMemo(() => {
    if (!isExpanded) return recentRecords || [];
    return allRecords || recentRecords || [];
  }, [allRecords, isExpanded, recentRecords]);

  const sectionTitle = isExpanded
    ? t('userCenter.all_records_count', {
      count: recordsToShow.length,
    })
    : t('userCenter.recent_records');

  const sectionHint = isExpanded
    ? t('userCenter.all_records_hint', {
      count: ALL_RECORD_LIMIT,
    })
    : t('userCenter.recent_records_hint', {
      count: 10,
    });

  const buttonLabel = isLoadingAll
    ? t('userCenter.loading_records')
    : isExpanded
      ? t('userCenter.collapse_records')
      : t('userCenter.view_all_records');

  const handleToggleRecords = useCallback(async () => {
    if (isExpanded) {
      setIsExpanded(false);
      setLoadError('');
      return;
    }

    setIsExpanded(true);
    setLoadError('');
    if (allRecords) {
      return;
    }

    if (!token) {
      setLoadError(t('userCenter.records_load_failed'));
      return;
    }

    setIsLoadingAll(true);
    try {
      const records = await AuthService.getRecentRecords(token, ALL_RECORD_LIMIT);
      setAllRecords(Array.isArray(records) ? records : []);
    } catch (error) {
      console.error('Load all user records failed:', error);
      setLoadError(t('userCenter.records_load_failed'));
    } finally {
      setIsLoadingAll(false);
    }
  }, [allRecords, isExpanded, t, token]);

  const hasRecords = recordsToShow.length > 0;
  const shouldShowTable = hasRecords || isLoadingAll || loadError;

  return (
    <section className={`user-center-card user-center-record-card ${isExpanded ? 'is-expanded' : ''}`}>
      <div className="user-center-section-head user-center-record-section-head">
        <div className="user-center-record-title-block">
          <h3>{sectionTitle}</h3>
          <p className="user-center-section-copy">{sectionHint}</p>
        </div>
        <button
          type="button"
          className="user-center-link-btn user-center-record-toggle"
          onClick={handleToggleRecords}
          disabled={isLoadingAll}
          aria-expanded={isExpanded}
        >
          {buttonLabel}
        </button>
      </div>

      {shouldShowTable ? (
        <div className="user-center-record-table-wrap">
          <div className="user-center-record-table">
            <div className="user-center-record-head">
              <div>{t('userCenter.record_file_name')}</div>
              <div>{t('userCenter.record_conversion')}</div>
              <div>{t('userCenter.record_status')}</div>
              <div>{t('userCenter.record_completed_at')}</div>
            </div>
            <div className="user-center-record-body">
              {isLoadingAll ? (
                <div className="user-center-record-row user-center-record-message-row">
                  <div className="user-center-record-col">
                    {t('userCenter.loading_records')}
                  </div>
                </div>
              ) : null}
              {loadError ? (
                <div className="user-center-record-row user-center-record-message-row is-error">
                  <div className="user-center-record-col">{loadError}</div>
                </div>
              ) : null}
              {recordsToShow.map((record, index) => {
                const fileName = record.fileName || t('userCenter.record_file_fallback');
                const fileSize = formatFileSize(record.fileSize);
                const sourceFormat = record.sourceFormat || t('userCenter.record_format_fallback');
                const targetFormat = record.targetFormat || t('userCenter.record_format_fallback');
                const recordTime = record.completedAt || record.createdAt;
                const displayTime = recordTime
                  ? formatDateTime(recordTime)
                  : t('userCenter.record_time_fallback');
                const statusClassName = normalizeRecordStatus(record.status);

                return (
                  <div className="user-center-record-row" key={getRecordKey(record, index)}>
                    <div className="user-center-record-col user-center-record-file">
                      <span className="user-center-record-label">{t('userCenter.record_file_name')}</span>
                      <span className="user-center-record-file-stack">
                        <strong className="user-center-record-file-name">{fileName}</strong>
                        {fileSize ? (
                          <span className="user-center-record-file-meta">{fileSize}</span>
                        ) : null}
                      </span>
                    </div>
                    <div className="user-center-record-col">
                      <span className="user-center-record-label">{t('userCenter.record_conversion')}</span>
                      <span>{sourceFormat} {'->'} {targetFormat}</span>
                    </div>
                    <div className="user-center-record-col">
                      <span className="user-center-record-label">{t('userCenter.record_status')}</span>
                      <span className={`user-center-record-status is-${statusClassName}`}>
                        {formatRecordStatus(record.status, t)}
                      </span>
                    </div>
                    <div className="user-center-record-col">
                      <span className="user-center-record-label">{t('userCenter.record_completed_at')}</span>
                      <span>{displayTime}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        <div className="user-center-empty-block">
          <p className="user-center-empty-title">{t('userCenter.no_records')}</p>
          <p className="user-center-empty">{t('userCenter.no_records_hint')}</p>
        </div>
      )}
    </section>
  );
}

export default UserCenterRecords;
