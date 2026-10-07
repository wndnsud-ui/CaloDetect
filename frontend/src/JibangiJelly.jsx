import React,{useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {createModel,createItem,jellyMaterial,disposeModel} from './jibangiModel';

export default function JibangiJelly({outfit='basic',interactive=false,pose='standing'}){
 const host=useRef(null),angle=useRef(0),wave=useRef(0),jump=useRef(0),pointer=useRef({x:0,y:0}),hover=useRef(0),drag=useRef(null),previous=useRef(outfit),pause=useRef(false);
 const [failed,setFailed]=useState(false),[paused,setPaused]=useState(false),[fallback,setFallback]=useState(false);
 useEffect(()=>{pause.current=paused;},[paused]);
 useEffect(()=>{
  const el=host.current;let renderer;
  try{renderer=new THREE.WebGLRenderer({alpha:true,antialias:true});}catch{setFailed(true);return;}
  renderer.setPixelRatio(Math.min(window.devicePixelRatio,interactive?1.75:1.25));renderer.setClearColor(0,0);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;el.appendChild(renderer.domElement);
  const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(32,1,.1,100);camera.position.set(0,1.2,7.8);camera.lookAt(0,.25,0);
  const room=new RoomEnvironment(),pmrem=new THREE.PMREMGenerator(renderer),environment=pmrem.fromScene(room,.06);scene.environment=environment.texture;scene.environmentIntensity=.55;room.dispose();pmrem.dispose();scene.add(new THREE.HemisphereLight(0xfff8e7,0xb2cabb,.8));
  for(const [color,power,p] of [[0xfff4df,2.8,[-3,5,5]],[0xe5f5ff,1.1,[4,2,4]],[0xffffff,2.4,[2,4,-3]]]){const light=new THREE.DirectionalLight(color,power);light.position.set(...p);scene.add(light);}
  const shadowCanvas=document.createElement('canvas');shadowCanvas.width=128;shadowCanvas.height=128;const ctx=shadowCanvas.getContext('2d'),gradient=ctx.createRadialGradient(64,64,5,64,64,64);gradient.addColorStop(0,'rgba(83,110,70,.26)');gradient.addColorStop(.45,'rgba(83,110,70,.15)');gradient.addColorStop(1,'rgba(83,110,70,0)');ctx.fillStyle=gradient;ctx.fillRect(0,0,128,128);
  const texture=new THREE.CanvasTexture(shadowCanvas),shadowMat=new THREE.MeshBasicMaterial({map:texture,transparent:true,depthWrite:false,opacity:.8}),shadow=new THREE.Mesh(new THREE.PlaneGeometry(3.5,2.8),shadowMat);shadow.rotation.x=-Math.PI/2;shadow.position.y=-1.29;scene.add(shadow);
  let body,armL,armR,leaf,face,eyes=[],glints=[],cancelled=false,ready=false,spinStart=0,velocity=0,usedFallback=false;
  const loader=new GLTFLoader(),changed=previous.current!==outfit;previous.current=outfit;
  async function asset(url,factory){try{return (await loader.loadAsync(url)).scene;}catch{usedFallback=true;if(!cancelled)setFallback(true);return factory();}}
  async function setup(){
   const model=await asset('/models/character/jibang.glb',createModel);if(cancelled){disposeModel(model);return;}body=model;scene.add(body);armL=body.getObjectByName('LeftHand');armR=body.getObjectByName('RightHand');leaf=body.getObjectByName('Leaf');face=body.getObjectByName('Face');eyes=['EyeLeft','EyeRight'].map(n=>body.getObjectByName(n));glints=['EyeGlintLeft','EyeGlintRight'].map(n=>body.getObjectByName(n));
   if(!interactive&&pose!=='heart')body.traverse(n=>{if(n.material?.isMeshPhysicalMaterial)n.material.transmission=0;});
   const items=outfit==='crown'?['ribbon','sport','crown']:outfit==='sport'?['ribbon','sport']:outfit==='ribbon'?['ribbon']:[];
   for(const item of items){const model=await asset(`/models/items/${item}.glb`,()=>createItem(item));if(cancelled){disposeModel(model);return;}body.getObjectByName(item==='sport'?'BodyAnchor':'HeadAnchor').add(model);}
   if(pose==='heart'){
    const shape=new THREE.Shape();shape.moveTo(0,-.38);shape.bezierCurveTo(-.08,-.28,-.55,.03,-.55,.27);shape.bezierCurveTo(-.55,.59,-.17,.66,0,.40);shape.bezierCurveTo(.17,.66,.55,.59,.55,.27);shape.bezierCurveTo(.55,.03,.08,-.28,0,-.38);
    const heart=new THREE.Mesh(new THREE.ExtrudeGeometry(shape,{depth:.14,bevelEnabled:true,bevelSegments:4,steps:1,bevelSize:.06,bevelThickness:.06,curveSegments:24}),jellyMaterial('#ef9b9a','cheek'));heart.position.set(0,-.68,.87);heart.scale.setScalar(.9);body.getObjectByName('BodyAnchor').add(heart);
    armL.position.set(-.36,-.42,.97);armL.rotation.z=-.45;armR.position.set(.32,-.57,.99);armR.rotation.z=1.1;
    for(const side of [-1,1])for(let i=0;i<6;i++){const mesh=new THREE.Mesh(new THREE.SphereGeometry(1,24,16),jellyMaterial(i%2?'#add68b':'#c6e2a2','leaf'));if(i===5){mesh.position.set(side*.98,-1.12,.58);mesh.scale.set(.38,.13,.12);mesh.rotation.z=side*.3;}else{mesh.position.set(side*(1+i*.16),-.94+i*.19,-.5);mesh.scale.set(.16,.38,.10);mesh.rotation.z=side*(-.45+i*.18);}scene.add(mesh);}
   }
   body.rotation.y=angle.current;spinStart=changed?performance.now():0;ready=true;el.dataset.model=usedFallback?'fallback':'glb';
  }
  setup().catch(()=>{if(!cancelled)setFailed(true);});
  function resize(){const w=el.clientWidth||300,h=el.clientHeight||300;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();}
  const observer=new ResizeObserver(resize);observer.observe(el);resize();const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');let visible=true;const visibility=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;});visibility.observe(el);let last=performance.now(),time=0,frames=0,measurement=performance.now();
  renderer.setAnimationLoop(now=>{
   const dt=Math.min((now-last)/1000,.05);last=now;if(!visible||document.hidden||!ready)return;const animate=!pause.current&&!reduced.matches;if(animate)time+=dt;
   const spin=spinStart&&animate?Math.min((now-spinStart)/1250,1):0,target=angle.current+(spinStart&&animate?Math.PI*2*(1-Math.pow(1-spin,3)):0)+(animate?Math.sin(time*.7)*.04:0),old=body.rotation.y;
   body.rotation.y=animate?THREE.MathUtils.damp(old,target,12.5,dt):angle.current;velocity=animate?THREE.MathUtils.damp(velocity,(body.rotation.y-old)/Math.max(dt,.001),8,dt):0;
   if(spinStart&&animate&&spin===1){body.rotation.y-=Math.PI*2;spinStart=0;}
   const lag=THREE.MathUtils.clamp(-velocity*.035,-.18,.18);leaf.rotation.y=animate?THREE.MathUtils.damp(leaf.rotation.y,lag,4.5,dt):0;leaf.rotation.z=animate?Math.sin(time*1.9)*.035:0;armL.rotation.y=armR.rotation.y=animate?THREE.MathUtils.damp(armR.rotation.y,lag*.6,6.7,dt):0;
   const elapsed=(now-jump.current)/1000,jumping=animate&&jump.current&&elapsed<.85,bounce=jumping?Math.sin(Math.min(elapsed/.65,1)*Math.PI)*.28:0,squash=jumping?Math.sin(elapsed*18)*Math.exp(-elapsed*3)*.055:0,breath=animate?Math.sin(time*2.1)*.012:0;
   body.position.y=(animate?Math.sin(time*2.1)*.025:0)+bounce;body.scale.set(1-breath*.45-squash*.5,1+breath+squash,1-breath*.45-squash*.5);shadow.scale.setScalar(1+bounce*.5);shadowMat.opacity=.8-bounce*.8;
   const blinking=animate&&(time%4.3>4.13||now-hover.current<150);eyes.forEach(eye=>eye.scale.y=.11*(blinking?.12:1));glints.forEach(g=>g.visible=!blinking);
   face.rotation.y=animate?THREE.MathUtils.damp(face.rotation.y,pointer.current.x*.035,5,dt):0;face.rotation.x=animate?THREE.MathUtils.damp(face.rotation.x,-pointer.current.y*.018,5,dt):0;
   armR.rotation.z=pose==='heart'?1.1:animate?Math.sin(time*2.2)*.10:0;if(now<wave.current&&animate&&pose!=='heart')armR.rotation.z=Math.sin(time*12)*.4+.5;renderer.render(scene,camera);
   frames++;if(now-measurement>1000){el.dataset.fps=String(Math.round(frames*1000/(now-measurement)));frames=0;measurement=now;}
  });
  return()=>{cancelled=true;observer.disconnect();visibility.disconnect();renderer.setAnimationLoop(null);disposeModel(scene);texture.dispose();environment.dispose();renderer.dispose();renderer.domElement.remove();delete el.dataset.model;};
 },[outfit,pose,interactive]);
 return <div className={`jibangi-model ${interactive?'interactive':''}`}><div ref={host} className="jibangi-canvas" role="img" aria-label="말랑한 3D 지방이" onPointerEnter={()=>hover.current=performance.now()} onPointerLeave={()=>{pointer.current={x:0,y:0};}} onPointerDown={e=>{if(!interactive)return;drag.current={x:e.clientX,start:e.clientX,y:e.clientY,moved:false};e.currentTarget.setPointerCapture(e.pointerId);}} onPointerMove={e=>{const r=e.currentTarget.getBoundingClientRect();pointer.current={x:(e.clientX-r.left)/r.width*2-1,y:(e.clientY-r.top)/r.height*2-1};if(!drag.current)return;angle.current+=(e.clientX-drag.current.x)*.012;drag.current.x=e.clientX;if(Math.hypot(e.clientX-drag.current.start,e.clientY-drag.current.y)>6)drag.current.moved=true;}} onPointerUp={()=>{if(drag.current&&!drag.current.moved)jump.current=performance.now();drag.current=null;}} onPointerCancel={()=>{drag.current=null;}}/>{failed&&<p role="alert">3D 화면을 사용할 수 없습니다. 브라우저의 하드웨어 가속을 확인해 주세요.</p>}{fallback&&interactive&&<p className="muted" role="status">모델을 불러오지 못해 기본 3D로 표시하고 있어요.</p>}{interactive&&<><p className="muted">마우스나 손가락으로 돌리고, 톡 눌러보세요</p><div className="model-controls"><button onClick={()=>{angle.current-=.35;}} aria-label="왼쪽 회전">↶</button><button onClick={()=>{angle.current=0;}}>정면</button><button onClick={()=>{angle.current+=.35;}} aria-label="오른쪽 회전">↷</button><button onClick={()=>{jump.current=performance.now();}}>톡 점프</button><button onClick={()=>{wave.current=performance.now()+2500;}}>손 흔들기</button><button aria-pressed={paused} onClick={()=>setPaused(value=>!value)}>{paused?'움직이기':'동작 멈춤'}</button></div></>}</div>;
}
