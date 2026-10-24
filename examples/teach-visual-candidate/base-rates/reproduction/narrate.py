#!/usr/bin/env python3
"""Native local TTS of reviewed prose, then ffmpeg of sandbox-generated PNGs.
No lesson JavaScript is evaluated here. No network or paid voice provider.
"""
import json,subprocess
from pathlib import Path
base=Path(__file__).resolve().parents[1]
render=base/'results/render-04'
evidence=json.loads((render/'render-evidence.json').read_text())
work=base/'results/narration-compatible';work.mkdir(exist_ok=False)
video=base/'source/videos';video.mkdir(exist_ok=True)
def run(args):subprocess.run(args,check=True,stdout=subprocess.DEVNULL)
def duration(p):return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(p)],text=True))
def stamp(t):
 ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}'
scenes=[];start=0;vtt=['WEBVTT','']
for i,sc in enumerate(evidence['meta']['scenes']):
 text=work/f'{i}.txt';text.write_text(sc['say'])
 audio=work/f'{i}.aiff';run(['say','-v','Samantha','-r','145','-f',str(text),'-o',str(audio)])
 voice=duration(audio);dur=round((voice+1.7)*24)/24
 manifest=work/f'{i}.frames.txt'
 rows=[]
 for j in range(9):
  f=render/'frames'/f'scene-{i}-{j}.png';rows.extend([f"file '{f}'",f'duration {0.15 if j<8 else dur-1.2:.9f}'])
 rows.append(f"file '{f}'");manifest.write_text('\n'.join(rows)+'\n')
 clip=work/f'{i}.mp4'
 run(['ffmpeg','-v','error','-y','-safe','0','-f','concat','-i',str(manifest),'-i',str(audio),'-af','adelay=1300:all=1,apad','-t',str(dur),'-vf','fps=24,tpad=stop_mode=clone:stop_duration=120','-fps_mode','cfr','-r','24','-c:v','libvpx-vp9','-deadline','realtime','-cpu-used','8','-threads','2','-b:v','0','-pix_fmt','yuv420p','-crf','30','-c:a','libopus','-b:a','128k','-movflags','+faststart',str(clip)])
 run(['ffmpeg','-v','error','-y','-safe','0','-f','concat','-i',str(manifest),'-i',str(audio),'-af','adelay=1300:all=1,apad','-t',str(dur),'-vf','fps=24,tpad=stop_mode=clone:stop_duration=120','-fps_mode','cfr','-r','24','-c:v','libx264','-pix_fmt','yuv420p','-crf','22','-c:a','aac','-b:a','128k','-movflags','+faststart',str(work/f'{i}-h264.mp4')])
 scenes.append(dict(start=start,dur=dur,voiceAt=start+1.3,voiceDur=voice))
 vtt.extend([str(i+1),f'{stamp(start+1.3)} --> {stamp(start+dur)}',sc['say'],''])
 start+=dur
concat=work/'clips.txt';concat.write_text('\n'.join(f"file '{work/f'{i}.mp4'}'" for i in range(7))+'\n')
run(['ffmpeg','-v','error','-y','-safe','0','-f','concat','-i',str(concat),'-c','copy','-movflags','+faststart',str(video/'base-rates.mp4')])
compat=work/'h264-clips.txt';compat.write_text('\n'.join(f"file '{work/f'{i}-h264.mp4'}'" for i in range(7))+'\n')
run(['ffmpeg','-v','error','-y','-safe','0','-f','concat','-i',str(compat),'-c','copy','-movflags','+faststart',str(video/'base-rates-h264.mp4')])
(video/'base-rates.vtt').write_text('\n'.join(vtt)+'\n')
timing=dict(scenes=scenes,total=start);(work/'timing.json').write_text(json.dumps(timing,indent=2)+'\n')
manifest=base/'source/course.json';data=json.loads(manifest.read_text());data['renderTiming']=timing;manifest.write_text(json.dumps(data,indent=2)+'\n')
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video/'base-rates.mp4')],text=True));(work/'probe.json').write_text(json.dumps(probe,indent=2))
run(['ffmpeg','-v','error','-i',str(video/'base-rates.mp4'),'-f','null','-'])
print(json.dumps({'duration':start,'actual':duration(video/'base-rates.mp4'),'words':sum(len(s['say'].split()) for s in evidence['meta']['scenes']),'voice':'Samantha','rate':145}))

# Both tracks must cover every authored hold, including the last spoken scene.
for name in ['base-rates.mp4','base-rates-h264.mp4']:
    details=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,codec_name,duration,nb_frames','-of','json',str(video/name)],text=True))
    stream=next(s for s in details['streams'] if s['codec_type']=='video')
    if abs(float(stream['duration'])-start)>.1 or int(stream['nb_frames'])!=round(start*24):
        raise RuntimeError('Video track does not cover the full narrated timeline')
    (work/(name+'.probe.json')).write_text(json.dumps(details,indent=2)+'\n')
    run(['ffmpeg','-v','error','-i',str(video/name),'-f','null','-'])
