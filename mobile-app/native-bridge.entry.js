import { Capacitor, CapacitorHttp } from "@capacitor/core";
import { SpeechRecognition } from "@capgo/capacitor-speech-recognition";
const native=Capacitor.isNativePlatform();
window.MIKAMIKE_NATIVE=native;
window.MIKAMIKE_API_BASE=native?"https://app.mikamike.fr/api/v1":"/api/v1";
let handles=[];
async function clearHandles(){const current=handles;handles=[];await Promise.all(current.map(h=>h?.remove?.().catch(()=>{})));}
window.MikaNativeHttp=native?{async request({path,method="GET",headers={},body=null}){const result=await CapacitorHttp.request({url:`https://app.mikamike.fr/api/v1${path}`,method,headers,data:body?JSON.parse(body):undefined,connectTimeout:15000,readTimeout:30000});return{status:result.status,data:result.data,headers:result.headers};}}:null;
window.MikaNativeSpeech=native?{
  available:true,
  async start({language="fr-FR",onPartial,onState,onError}={}){
    await clearHandles();
    const permissions=await SpeechRecognition.requestPermissions();
    if(permissions.speechRecognition!=="granted")throw new Error("Autorisation micro refusée.");
    const support=await SpeechRecognition.available();
    if(!support.available)throw new Error("Reconnaissance vocale indisponible sur cet appareil.");
    handles.push(await SpeechRecognition.addListener("partialResults",(event)=>{const text=event.accumulatedText||event.matches?.[0]||"";if(text)onPartial?.(text);}));
    handles.push(await SpeechRecognition.addListener("listeningState",(event)=>{const listening=event.status==="started"||event.state==="started"||event.state==="startingListening";onState?.(listening);}));
    handles.push(await SpeechRecognition.addListener("error",(event)=>onError?.(event.message||event.code||"Erreur de reconnaissance vocale.")));
    await SpeechRecognition.start({language,maxResults:3,partialResults:true,popup:false,contextualStrings:["MikaMike","mathématiques","fraction","équation","géométrie"]});
  },
  async stop(){try{await SpeechRecognition.stop();}finally{await clearHandles();}}
}:null;
