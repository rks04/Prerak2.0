import { create } from "zustand";

interface CodeState {
  activeFile: string | null;
  setActiveFile: (file: string | null) => void;
}

export const useCodeStore = create<CodeState>((set) => ({
  activeFile: null,
  setActiveFile: (file) => set({ activeFile: file }),
}));
