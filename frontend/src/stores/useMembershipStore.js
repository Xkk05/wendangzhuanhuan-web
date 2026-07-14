import { create } from 'zustand';

export const useMembershipStore = create((set) => ({
  isUpgradeModalVisible: false,
  upgradeMessage: '',
  paymentUrl: '',
  source: 'system',
  openUpgradeModal: ({ message = '', paymentUrl = '' } = {}) =>
    set({
      isUpgradeModalVisible: true,
      upgradeMessage: message,
      paymentUrl,
      source: 'system',
    }),
  openPurchaseModal: () =>
    set({
      isUpgradeModalVisible: true,
      upgradeMessage: '',
      paymentUrl: '',
      source: 'manual',
    }),
  closeUpgradeModal: () =>
    set({
      isUpgradeModalVisible: false,
      upgradeMessage: '',
      paymentUrl: '',
      source: 'system',
    }),
}));
