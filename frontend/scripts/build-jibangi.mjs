import {mkdir,writeFile} from 'node:fs/promises';
import {GLTFExporter} from 'three/addons/exporters/GLTFExporter.js';
import {createModel,createItem,disposeModel} from '../src/jibangiModel.js';
// GLTFExporter uses the browser FileReader API; provide its two Blob operations in Node.
globalThis.FileReader=class {
 readAsArrayBuffer(blob){blob.arrayBuffer().then(value=>{this.result=value;this.onloadend?.();});}
 readAsDataURL(blob){blob.arrayBuffer().then(value=>{this.result=`data:${blob.type};base64,${Buffer.from(value).toString('base64')}`;this.onloadend?.();});}
};
const root=new URL('../public/models/',import.meta.url);
async function save(model,file){const target=new URL(file,root);await mkdir(new URL('.',target),{recursive:true});const data=await new GLTFExporter().parseAsync(model,{binary:true,onlyVisible:false});await writeFile(target,Buffer.from(data));let triangles=0;model.traverse(n=>{if(n.isMesh)triangles+=(n.geometry.index?.count||n.geometry.attributes.position.count)/3;});console.log(`${file}: ${data.byteLength} bytes, ${triangles} triangles`);disposeModel(model);}
await save(createModel(),'character/jibang.glb');
for(const item of ['ribbon','sport','crown'])await save(createItem(item),`items/${item}.glb`);
