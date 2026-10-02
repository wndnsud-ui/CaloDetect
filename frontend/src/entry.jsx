import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import App from './main';
import Landing from './Landing';
function Entry(){const[page,setPage]=useState(null);return page===null?<Landing onOpen={setPage}/>:<App initialPage={page} onHomepage={()=>setPage(null)}/>;}
createRoot(document.getElementById('root')).render(<Entry/>);
