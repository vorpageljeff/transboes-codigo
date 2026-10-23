// Run inside the Uptime Kuma container with KUMA_USER and KUMA_PASSWORD in environment.
// Credentials are never printed. Existing installations require their existing credentials.
const { io } = require('socket.io-client');
const socket=io('http://127.0.0.1:3001', {transports:['websocket'],reconnection:false});
let monitors={};
socket.on('monitorList', data=>{monitors=data;});
const emit=(name,...args)=>new Promise((resolve,reject)=>socket.timeout(15000).emit(name,...args,(err,result)=>err?reject(err):resolve(result)));
const deadline=setTimeout(()=>{console.error('Monitoring configuration timeout');process.exit(1);},45000);
socket.on('connect',async()=>{
 try {
  if(!process.env.KUMA_USER||!process.env.KUMA_PASSWORD)throw new Error('Missing private monitoring credentials');
  await emit('setup',process.env.KUMA_USER,process.env.KUMA_PASSWORD);
  const login=await emit('login',{username:process.env.KUMA_USER,password:process.env.KUMA_PASSWORD,token:''});
  if(!login.ok)throw new Error('Monitoring authentication failed');
  for(const item of [{name:'TransBoes API e banco',url:process.env.API_HEALTH_URL},{name:'TransBoes portal',url:process.env.PORTAL_URL}]){
   if(!item.url)throw new Error('Missing monitoring URL');
   if(Object.values(monitors).some(m=>m.url===item.url))continue;
   const result=await emit('add',{...item,type:'http',active:true,interval:60,retryInterval:20,maxretries:2,timeout:10,method:'GET',accepted_statuscodes:['200-299'],notificationIDList:{},ignoreTls:false,upsideDown:false,maxredirects:3,expiryNotification:true});
   if(!result.ok)throw new Error(result.msg||'Cannot add monitor');
  }
  console.log('HTTPS monitors configured. Notification delivery requires a configured destination.');
  clearTimeout(deadline);socket.disconnect();
 }catch(error){console.error(error.message);clearTimeout(deadline);socket.disconnect();process.exitCode=1;}
});
