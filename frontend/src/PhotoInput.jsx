import React, { useEffect, useRef, useState } from 'react';

export default function PhotoInput({file, onChange, busy = false}) {
  const picker = useRef(null), mobileCamera = useRef(null), video = useRef(null);
  const stream = useRef(null), request = useRef(0);
  const [preview, setPreview] = useState(''), [error, setError] = useState('');
  const [camera, setCamera] = useState(false), [starting, setStarting] = useState(false);
  function stopCamera() {
    request.current += 1;
    stream.current?.getTracks().forEach(track => track.stop());
    stream.current = null;
    setCamera(false); setStarting(false);
  }
  useEffect(() => {
    if (!file) {setPreview(''); return;}
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => () => {
    request.current += 1;
    stream.current?.getTracks().forEach(track => track.stop());
  }, []);
  useEffect(() => {
    if (camera && video.current) video.current.srcObject = stream.current;
  }, [camera]);
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
  function inputChanged(event) {
    selectFile(event.target.files?.[0]);
    event.target.value = '';
  }
  async function openCamera() {
    setError('');
    if (/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
      mobileCamera.current.click(); return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('카메라 촬영은 HTTPS 또는 localhost에서 지원됩니다. 사진 선택으로 업로드할 수 있습니다.'); return;
    }
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
  function capture() {
    const source = video.current;
    if (!source?.videoWidth) {setError('카메라가 준비될 때까지 잠시 기다려 주세요.'); return;}
    const canvas = document.createElement('canvas');
    canvas.width = source.videoWidth; canvas.height = source.videoHeight;
    canvas.getContext('2d').drawImage(source, 0, 0);
    const id = request.current;
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
