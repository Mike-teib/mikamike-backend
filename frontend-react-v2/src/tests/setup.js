import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock HTMLCanvasElement getContext for ArdoiseCanvas testing in jsdom
HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
  beginPath: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  stroke: vi.fn(),
  clearRect: vi.fn(),
  lineCap: '',
  lineJoin: '',
  strokeStyle: '',
  lineWidth: 1
});
