import { create } from 'zustand';

import { THEME_STORAGE_KEY } from './config';
import type { ConfirmationDialogState, ErrorDialogState, ModalState, ThemeMode } from './types';

type ThemeState = {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
};

function getInitialThemeMode(): ThemeMode {
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === 'light' || stored === 'dark' || stored === 'system') {
    return stored;
  }
  return 'system';
}

export const useThemeStore = create<ThemeState>((set) => ({
  mode: getInitialThemeMode(),
  setMode: (mode) => {
    window.localStorage.setItem(THEME_STORAGE_KEY, mode);
    set({ mode });
  },
}));

type ErrorDialogStore = {
  dialog: ErrorDialogState;
  openDialog: (input: Omit<ErrorDialogState, 'open'>) => void;
  closeDialog: () => void;
};

export const useErrorDialogStore = create<ErrorDialogStore>((set) => ({
  dialog: {
    open: false,
    title: '',
    code: '',
    message: '',
    status: 0,
  },
  openDialog: (input) => set({ dialog: { ...input, open: true } }),
  closeDialog: () =>
    set((state) => ({
      dialog: {
        ...state.dialog,
        open: false,
      },
    })),
}));

type ConfirmationDialogStore = {
  dialog: ConfirmationDialogState;
  openDialog: (input: Omit<ConfirmationDialogState, 'open'>) => void;
  closeDialog: () => void;
};

export const useConfirmationDialogStore = create<ConfirmationDialogStore>((set) => ({
  dialog: {
    open: false,
    title: '',
    description: '',
    confirmLabel: '',
    danger: false,
    onConfirm: null,
  },
  openDialog: (input) => set({ dialog: { ...input, open: true } }),
  closeDialog: () =>
    set((state) => ({
      dialog: {
        ...state.dialog,
        open: false,
        onConfirm: null,
      },
    })),
}));

type UiState = {
  selectedChatId: number | null;
  setSelectedChatId: (chatId: number | null) => void;
  commentsRootId: number | null;
  setCommentsRootId: (messageId: number | null) => void;
  isMenuOpen: boolean;
  setMenuOpen: (value: boolean) => void;
  isMobileInfoOpen: boolean;
  setMobileInfoOpen: (value: boolean) => void;
  modal: ModalState;
  openModal: (modal: ModalState) => void;
  closeModal: () => void;
};

export const useUiStore = create<UiState>((set) => ({
  selectedChatId: null,
  setSelectedChatId: (chatId) => set({ selectedChatId: chatId }),
  commentsRootId: null,
  setCommentsRootId: (messageId) => set({ commentsRootId: messageId }),
  isMenuOpen: false,
  setMenuOpen: (value) => set({ isMenuOpen: value }),
  isMobileInfoOpen: window.matchMedia('(min-width: 1201px)').matches,
  setMobileInfoOpen: (value) => set({ isMobileInfoOpen: value }),
  modal: { type: 'none' },
  openModal: (modal) => set({ modal }),
  closeModal: () => set({ modal: { type: 'none' } }),
}));

type AvatarVersionState = {
  userVersions: Record<number, number>;
  chatVersions: Record<number, number>;
  bumpUserVersion: (userId: number) => void;
  bumpChatVersion: (chatId: number) => void;
};

export const useAvatarVersionStore = create<AvatarVersionState>((set) => ({
  userVersions: {},
  chatVersions: {},
  bumpUserVersion: (userId) =>
    set((state) => ({
      userVersions: {
        ...state.userVersions,
        [userId]: Date.now(),
      },
    })),
  bumpChatVersion: (chatId) =>
    set((state) => ({
      chatVersions: {
        ...state.chatVersions,
        [chatId]: Date.now(),
      },
    })),
}));
