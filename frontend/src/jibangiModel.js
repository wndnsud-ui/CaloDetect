import * as THREE from 'three';

export function jellyMaterial(color,part='body') {
 const settings={body:[.24,.15,.65],leaf:[.2,.2,.28],mint:[.26,.1,.35],cheek:[.3,.06,.12],eye:[.08,0,0]};
 const [roughness,transmission,thickness]=settings[part]||settings.body;
 return new THREE.MeshPhysicalMaterial({color,roughness,transmission,thickness,ior:1.45,metalness:0,clearcoat:.2,clearcoatRoughness:.12,attenuationColor:color,attenuationDistance:2.4});
}
export function createModel(){
 const root=new THREE.Group();root.name='JibangRoot';
 const geometry=new THREE.SphereGeometry(1,40,28);
 function ball(name,color,position,scale,part='body',parent=root){const mesh=new THREE.Mesh(geometry,jellyMaterial(color,part));mesh.name=name;mesh.position.set(...position);mesh.scale.set(...scale);parent.add(mesh);return mesh;}
 ball('Body','#fffbd6',[0,0,0],[1.08,1.15,.8]);
 function group(name,position,parent=root){const node=new THREE.Group();node.name=name;node.position.set(...position);parent.add(node);return node;}
 const left=group('LeftHand',[-.96,-.15,0]),right=group('RightHand',[.96,.05,0]);
 ball('LeftPalm','#ffedc5',[-.19,0,0],[.4,.24,.3],'body',left);
 ball('RightPalm','#ffedc5',[.18,.13,0],[.24,.42,.28],'body',right);
 ball('LeftFoot','#70b89a',[-.48,-1.08,.2],[.3,.18,.4],'mint');ball('RightFoot','#70b89a',[.48,-1.08,.2],[.3,.18,.4],'mint');
 const leaf=group('Leaf',[0,1.18,0]);
 ball('LeafLeft','#94cc45',[-.23,.06,0],[.43,.2,.15],'leaf',leaf).rotation.z=-.55;
 ball('LeafRight','#82be39',[.2,.17,0],[.2,.44,.15],'leaf',leaf).rotation.z=-.6;
 const face=group('Face',[0,0,0]);
 ball('EyeLeft','#263c2a',[-.36,.18,.755],[.07,.11,.045],'eye',face);ball('EyeRight','#263c2a',[.36,.18,.755],[.07,.11,.045],'eye',face);
 ball('EyeGlintLeft','#fffdf4',[-.375,.215,.797],[.018,.025,.01],'eye',face);ball('EyeGlintRight','#fffdf4',[.345,.215,.797],[.018,.025,.01],'eye',face);
 ball('CheekLeft','#f3aca2',[-.58,-.07,.68],[.18,.09,.04],'cheek',face);ball('CheekRight','#f3aca2',[.58,-.07,.68],[.18,.09,.04],'cheek',face);
 ball('Mouth','#6c4436',[0,-.17,.79],[.14,.11,.035],'eye',face);ball('Tongue','#f49c99',[0,-.21,.823],[.10,.055,.012],'cheek',face);
 for(const name of ['HeadAnchor','FaceAnchor','BodyAnchor','LeftHandAnchor','RightHandAnchor'])group(name,[0,0,0]);
 root.userData={version:1,description:'CaloDetect soft jelly character; original proportions retained'};
 return root;
}
export function createItem(outfit){
 const group=new THREE.Group();group.name=`Item_${outfit}`;
 const geometry=new THREE.SphereGeometry(1,24,16);
 function ball(color,p,s){const mesh=new THREE.Mesh(geometry,jellyMaterial(color,'cheek'));mesh.position.set(...p);mesh.scale.set(...s);group.add(mesh);return mesh;}
 if(outfit==='ribbon'){
  ball('#ed8dab',[.57,1.04,.35],[.23,.13,.12]).rotation.z=-.5;ball('#ed8dab',[.88,1.10,.25],[.23,.13,.12]).rotation.z=.5;ball('#df7998',[.72,1.04,.4],[.10,.10,.10]);
 }else if(outfit==='sport'){
  ball('#f19bb0',[0,-.70,.02],[1.01,.35,.77]);ball('#fff6df',[0,-.52,.72],[.78,.035,.07]);ball('#7dc9c6',[1.2,-.22,.25],[.16,.33,.16]);
 }else if(outfit==='crown'){
  ball('#e9c356',[0,1.13,-.15],[.49,.12,.34]);for(let i=-1;i<=1;i++)ball('#f7d67c',[i*.28,1.32,-.1],[.09,.24,.09]);
 }
 return group;
}
export function disposeModel(root){const geometries=new Set(),materials=new Set();root.traverse(node=>{if(node.geometry)geometries.add(node.geometry);if(node.material)for(const mat of Array.isArray(node.material)?node.material:[node.material])materials.add(mat);});geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());}
