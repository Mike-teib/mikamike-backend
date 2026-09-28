import {cp,mkdir,rm} from "node:fs/promises";import {resolve} from "node:path";
const root=resolve(import.meta.dirname,"../..");const source=resolve(root,"frontend-vnext");const dest=resolve(import.meta.dirname,"../www");
await rm(dest,{recursive:true,force:true});await mkdir(dest,{recursive:true});await cp(source,dest,{recursive:true});console.log("frontend-vnext -> mobile-app/www");
