// JPG/PNG 선택·모바일 카메라 입력·PC 웹캠 촬영과 로컬 미리보기 UI.
// 파일 검사 후 상위 onChange로 전달하며 여기서 서버 업로드는 하지 않는다. 미리보기 URL과 카메라 트랙은 종료 시 해제한다.
import React, { useEffect, useRef, useState } from 'react';

// JPG/PNG 선택·모바일 카메라 입력·PC 웹캠 촬영과 로컬 미리보기 UI.
export default function PhotoInput({file, onChange, busy = false}) {
  // DOM input/video와 미디어 스트림은 렌더 상태 대신 ref로 보관한다.
  const picker = useRef(null), mobileCamera = useRef(null), video = useRef(null);
  // request 세대 번호를 카메라 시작/촬영 시 비교해 취소되거나 화면을 떠난 작업을 무시한다.
  const stream = useRef(null), request = useRef(0);
  const [preview, setPreview] = useState(''), [error, setError] = useState('');
  const [camera, setCamera] = useState(false), [starting, setStarting] = useState(false);
  // 요청 세대를 바꾸고 모든 미디어 트랙을 중지해 늦은 카메라 응답과 촬영을 무효화한다.
  function stopCamera() {
    request.current += 1;
    stream.current?.getTracks().forEach(track => track.stop());
    stream.current = null;
    setCamera(false); setStarting(false);
  }
  // 의존값 변경/마운트에 맞춰 외부 데이터 또는 브라우저 자원을 동기화한다. 반환하는 정리 함수는 이전 작업/자원을 해제한다.
  useEffect(() => {
    if (!file) {setPreview(''); return;}
    // 업로드 없이 로컬 Blob URL로 사진을 미리본다. 사진 변경/컴포넌트 종료 시 revoke한다.
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  // 의존값 변경/마운트에 맞춰 외부 데이터 또는 브라우저 자원을 동기화한다. 반환하는 정리 함수는 이전 작업/자원을 해제한다.
  useEffect(() => () => {
    request.current += 1;
    stream.current?.getTracks().forEach(track => track.stop());
  }, []);
  // 의존값 변경/마운트에 맞춰 외부 데이터 또는 브라우저 자원을 동기화한다. 반환하는 정리 함수는 이전 작업/자원을 해제한다.
  useEffect(() => {
    if (camera && video.current) video.current.srcObject = stream.current;
  }, [camera]);
  // JPG/PNG·0 초과/10MB 이하 조건을 검사한 뒤 카메라를 종료하고 상위에 파일을 전달한다.
  function selectFile(next) {
    if (!next) return;
    if (!['image/jpeg', 'image/png'].includes(next.type)) {
      setError('JPG 또는 PNG 사진을 선택해 주세요. 다른 형식은 JPG로 변환해 주세요.'); return;
    }
    if (!next.size || next.size > 10 * 1024 * 1024) {
      setError('사진은 0바이트보다 크고 10MB 이하여야 합니다.'); return;
    }
    setError(''); stopCamera(); onChange(next);
  }
  // 첫 파일을 선택하고 input 값을 비워 같은 파일도 다시 선택할 수 있게 한다.
  function inputChanged(event) {
    selectFile(event.target.files?.[0]);
    event.target.value = '';
  }
  // 모바일은 capture input을 사용하고 PC는 getUserMedia로 웹캠을 연다. 늦게 반환된 취소 요청의 트랙도 정리한다.
  async function openCamera() {
    setError('');
    if (/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
      mobileCamera.current.click(); return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('카메라 촬영은 HTTPS 또는 localhost에서 지원됩니다. 사진 선택으로 업로드할 수 있습니다.'); return;
    }
    // 이번 카메라 요청만 유효하게 표시한다. 권한 팝업이 늦게 끝나도 취소된 스트림을 다시 켜지 않는다.
    const id = ++request.current;
    setStarting(true);
    try {
      const media = await navigator.mediaDevices.getUserMedia({video: {facingMode: {ideal: 'environment'}}, audio: false});
      if (id !== request.current) {media.getTracks().forEach(track => track.stop()); return;}
      stream.current = media; setCamera(true);
    } catch (err) {
      if (id === request.current) setError(err.name === 'NotAllowedError'
        ? '카메라 권한을 허용해 주세요. 사진 선택으로도 업로드할 수 있습니다.'
        : '카메라를 사용할 수 없습니다. 연결 상태를 확인하거나 사진을 선택해 주세요.');
    } finally {if (id === request.current) setStarting(false);}
  }
  // 현재 비디오 프레임을 canvas의 JPEG Blob/File로 만들어 일반 사진 선택 검사를 재사용한다.
  function capture() {
    const source = video.current;
    if (!source?.videoWidth) {setError('카메라가 준비될 때까지 잠시 기다려 주세요.'); return;}
    const canvas = document.createElement('canvas');
    canvas.width = source.videoWidth; canvas.height = source.videoHeight;
    canvas.getContext('2d').drawImage(source, 0, 0);
    const id = request.current;
    // JPEG 인코딩은 비동기다. 완료 전에 촬영이 취소되면 Blob 결과를 버린다.
    canvas.toBlob(blob => {
      if (id !== request.current) return;
      if (!blob) {setError('촬영에 실패했습니다. 다시 촬영해 주세요.'); return;}
      selectFile(new File([blob], `meal-${Date.now()}.jpg`, {type: 'image/jpeg'}));
    }, 'image/jpeg', 0.9);
  }
  return <div className="photo-input">
    <input ref={picker} type="file" accept="image/jpeg,image/png" hidden onChange={inputChanged}/>
    <input ref={mobileCamera} type="file" accept="image/jpeg,image/png" capture="environment" hidden onChange={inputChanged}/>
    <div className="photo-actions">
      <button type="button" className="outline" disabled={busy || starting || camera} onClick={()=>picker.current.click()}>사진 선택</button>
      <button type="button" className="outline" disabled={busy || starting || camera} onClick={openCamera}>{starting ? '카메라 연결 중…' : '사진 바로 찍기'}</button>
    </div>
    <p className="muted">JPG/PNG · 최대 10MB · 음식이 잘 보이도록 촬영해 주세요.</p>
    {error && <p className="error" role="alert">{error}</p>}
    {starting && <button type="button" className="text-button" onClick={stopCamera}>카메라 연결 취소</button>}
    {camera && <div className="camera-preview"><video ref={video} autoPlay muted playsInline aria-label="촬영할 음식 미리보기"/><div className="photo-actions"><button type="button" className="primary" onClick={capture}>촬영하기</button><button type="button" className="text-button" onClick={stopCamera}>촬영 취소</button></div></div>}
    {preview && !camera && <div className="scan-preview"><img src={preview} alt="선택한 음식 사진 미리보기"/><p className="photo-filename">{file.name}</p><button type="button" className="text-button" disabled={busy} onClick={()=>{onChange(null);setError('');}}>사진 제거</button></div>}
  </div>;
}
