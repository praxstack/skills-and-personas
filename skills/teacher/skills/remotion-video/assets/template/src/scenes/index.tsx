// The film's scenes, split into the two layers Film.tsx draws:
//   Subject     the persistent graph (director.ts decides its state, place and the camera)
//   SceneWorld  things that live in the world and move with the camera (input panel, tree, tables, code)
//   SceneHud    screen-space things the camera does not move (title, question cards, comic bursts)
// A new film replaces the files in this folder; Film.tsx and kit/ stay.
import React from 'react';
import {useCurrentFrame} from 'remotion';
import {Graph} from '../kit/Graph';
import type {Cam} from '../kit/Camera';
import {MAP} from './data';
import {cameraAt, graphAt, placeAt} from './director';
import {ProblemHud, ProblemWorld} from './Problem';
import {BruteHud, BruteWorld} from './Brute';
import {IntuitionHud, IntuitionWorld} from './Intuition';
import {ApproachesWorld} from './Approaches';
import {CodeHud, CodeWorld} from './Code';

export {cameraAt};

export const Subject: React.FC = () => {
  const fr = useCurrentFrame();
  return <Graph data={MAP} st={graphAt(fr)} place={placeAt(fr)} uid="map" />;
};

export const SceneWorld: React.FC = () => (
  <>
    <ProblemWorld />
    <BruteWorld />
    <IntuitionWorld />
    <ApproachesWorld />
    <CodeWorld />
  </>
);

export const SceneHud: React.FC<{cam: Cam}> = ({cam}) => (
  <>
    <ProblemHud cam={cam} />
    <BruteHud />
    <IntuitionHud />
    <CodeHud cam={cam} />
  </>
);
