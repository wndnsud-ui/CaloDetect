// 리워드 창 공통 틀: role=dialog, 열릴 때 첫 버튼 포커스, Esc 닫기, 닫으면 여는 버튼으로 포커스 복귀(지시서 v3 §11-8).
import React, {useEffect, useRef} from 'react';

export default function RewardDialog({title, labelledBy, onClose, className = '', children}) {
  const box = useRef(null);
  useEffect(() => {
    const opener = document.activeElement;
    box.current?.querySelector('button, [href], input, select')?.focus();
    function key(event) { if (event.key === 'Escape') onClose?.(); }
    document.addEventListener('keydown', key);
    return () => { document.removeEventListener('keydown', key); if (opener?.focus) opener.focus(); };
  }, []);
  return <div className="reward-overlay" onMouseDown={event => { if (event.target === event.currentTarget) onClose?.(); }}>
    <div ref={box} className={`reward-dialog ${className}`} role="dialog" aria-modal="true" aria-labelledby={labelledBy} aria-label={labelledBy ? undefined : title}>
      {onClose && <button type="button" className="reward-dialog-close" aria-label="닫기" onClick={onClose}>×</button>}
      {children}
    </div>
  </div>;
}
