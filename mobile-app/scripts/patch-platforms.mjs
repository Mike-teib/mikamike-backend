import {readFile,writeFile} from "node:fs/promises";import {existsSync} from "node:fs";import {resolve} from "node:path";
const root=resolve(import.meta.dirname,"..");const plist=resolve(root,"ios/App/App/Info.plist");
if(existsSync(plist)){let text=await readFile(plist,"utf8");const a=[];
if(!text.includes("NSMicrophoneUsageDescription"))a.push("<key>NSMicrophoneUsageDescription</key><string>MikaMike utilise le micro uniquement quand l’élève active la dictée vocale.</string>");
if(!text.includes("NSSpeechRecognitionUsageDescription"))a.push("<key>NSSpeechRecognitionUsageDescription</key><string>MikaMike transforme la réponse dictée par l’élève en texte pour le tutorat.</string>");
if(a.length){text=text.replace("</dict>","  "+a.join("\n  ")+"\n</dict>");await writeFile(plist,text);console.log("Info.plist permissions ajoutées");}}
