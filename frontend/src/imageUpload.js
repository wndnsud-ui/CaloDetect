// 사진 업로드 공통 처리. 서버 기준(JPG/PNG, 10MB, 2500만 화소)을 넘지 않도록 긴 변 2048px 이하 JPEG로 바꿔 보낸다.
// 최신 휴대폰 사진(4800만 화소 등)과 HEIC도 브라우저가 열 수 있으면 변환된다. 디코딩에 실패하면 원본을 보내지 않는다.
export const MAX_SIDE = 2048;

export async function toJpeg(file) {
  const url = URL.createObjectURL(file);
  try {
    const image = await new Promise((resolve, reject) => { const img = new Image(); img.onload = () => resolve(img); img.onerror = reject; img.src = url; });
    const scale = Math.min(1, MAX_SIDE / Math.max(image.naturalWidth, image.naturalHeight));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(image.naturalWidth * scale); canvas.height = Math.round(image.naturalHeight * scale);
    canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9));
    if (!blob) throw new Error('encode');
    return blob;
  } finally { URL.revokeObjectURL(url); }
}
