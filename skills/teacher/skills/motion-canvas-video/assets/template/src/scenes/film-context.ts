import type {Camera, Chrome, Graph, InputPanel, World} from '../kit';

/** What every chapter gets: the world (layers + camera), the persistent subject, and shared panels. */
export interface Film {
  w: World;
  g: Graph;
  cam: Camera;
  input: InputPanel;
  chrome: Chrome;
}
