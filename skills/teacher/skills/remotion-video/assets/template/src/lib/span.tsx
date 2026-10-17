// <Span from to> mounts its children only between two absolute frames (a Remotion <Sequence> keyed to line
// ids: <Span from={fStart('p1')} to={fEnd('p3')}>). Inside, useF() still returns the ABSOLUTE frame, so
// scene code can keep using f('id') everywhere without offset arithmetic.
import React, {createContext, useContext} from 'react';
import {Sequence, useCurrentFrame} from 'remotion';

const Offset = createContext(0);

export const Span: React.FC<{from: number; to: number; name?: string; children: React.ReactNode}> = ({from, to, name, children}) => {
  const parent = useContext(Offset);
  return (
    <Sequence from={from - parent} durationInFrames={Math.max(1, to - from)} layout="none" name={name}>
      <Offset.Provider value={from}>{children}</Offset.Provider>
    </Sequence>
  );
};

/** absolute frame of the film, inside or outside a Span */
export const useF = () => useCurrentFrame() + useContext(Offset);
