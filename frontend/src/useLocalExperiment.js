import {useCallback,useEffect,useState} from 'react';
export default function useLocalExperiment(user,section,initial){
 const key=`calodetect-experiment-${user?.id||'guest'}-${section}`;
 const read=useCallback(()=>{try{return JSON.parse(localStorage.getItem(key))??initial;}catch{return initial;}},[key]);
 const [value,setValue]=useState(read),[storageError,setStorageError]=useState('');
 useEffect(()=>{setValue(read());setStorageError('');},[read]);
 const update=next=>setValue(current=>{const result=typeof next==='function'?next(current):next;try{localStorage.setItem(key,JSON.stringify(result));setStorageError('');}catch{setStorageError('브라우저에 저장하지 못했습니다. 이 화면을 닫으면 변경 내용이 사라질 수 있습니다.');}return result;});
 return [value,update,storageError];
}
