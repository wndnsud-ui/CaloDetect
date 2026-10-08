// 사진 분석의 대기·진행·성공·실패 상태와 탐지 결과를 표시한다. 탐지 실패 시에도 음식 직접 선택 흐름을 안내한다.
import React from 'react';

// 사진 분석의 대기·진행·성공·실패 상태와 탐지 결과를 표시한다. 탐지 실패 시에도 음식 직접 선택 흐름을 안내한다.
export default function ScanResult({status, error, result}) {
  if (status === 'working') return <p className="notice" role="status">사진을 업로드하고 음식을 분석하고 있습니다. 잠시 기다려 주세요.</p>;
  if (status === 'error') return <p className="error scan-feedback" role="alert">사진 분석 실패: {error}</p>;
  if (!result) return <p className="muted">사진 선택 후 사진 분석하기를 눌러 주세요. 직접 선택한 음식은 사진 분석 결과와 별개입니다.</p>;
  return <div className="scan-result" role="status">
    <strong>사진 분석 완료 · 인식된 음식 {result.detections.length}개</strong>
    {result.detections.length ? <ul>{result.detections.map(item => <li key={item.id}>
      <b>{item.predicted_label}</b><span>신뢰도 {Math.round(item.confidence * 100)}%</span>
    </li>)}</ul> : <p>이 사진에서는 음식을 인식하지 못했습니다. 다른 사진으로 다시 시도하거나 음식을 직접 추가해 주세요.</p>}
    {result.detections.length > 0 && <p>오른쪽의 음식명과 섭취량을 확인한 뒤 식단을 저장하세요.</p>}
  </div>;
}
