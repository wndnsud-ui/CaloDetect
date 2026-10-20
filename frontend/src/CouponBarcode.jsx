// 쿠폰 번호 CODE128 바코드 SVG(지시서 v3 §11-7). 스캔이 잘 되도록 흰 바탕·검은 막대·앞뒤 여백을 둔다.
import React, {useMemo} from 'react';
import {code128Bars} from './barcode';

export default function CouponBarcode({code, height = 80, className = ''}) {
  const layout = useMemo(() => { try { return code128Bars(code); } catch { return null; } }, [code]);
  if (!layout) return <p className="muted">바코드를 만들 수 없는 번호예요. 아래 번호를 보여 주세요.</p>;
  return <svg className={`coupon-barcode ${className}`} viewBox={`0 0 ${layout.width} 60`} preserveAspectRatio="none" style={{height}}
    role="img" aria-label={`쿠폰 바코드 ${code}`}>
    <rect width={layout.width} height="60" fill="#FFFFFF"/>
    <g fill="#111111">{layout.bars.map(bar => <rect key={bar.x} x={bar.x} y="0" width={bar.w} height="60"/>)}</g>
  </svg>;
}
