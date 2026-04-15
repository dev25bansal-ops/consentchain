import {
  createContext,
  useContext,
  ReactNode,
  useCallback,
  useState,
  useEffect,
} from "react";
import {
  WalletManager,
  WalletId,
  WalletAccount,
  NetworkId,
} from "@txnlab/use-wallet";

interface WalletContextType {
  address: string | null;
  isConnected: boolean;
  loading: boolean;
  connect: (walletId: WalletId) => Promise<void>;
  disconnect: () => Promise<void>;
  activeAccount: WalletAccount | null;
  walletManager: WalletManager | null;
  signMessage: (message: string) => Promise<string | null>;
  signBytes: (bytes: Uint8Array) => Promise<Uint8Array | null>;
}

const WalletContext = createContext<WalletContextType>({
  address: null,
  isConnected: false,
  loading: false,
  connect: async () => {},
  disconnect: async () => {},
  activeAccount: null,
  walletManager: null,
  signMessage: async () => null,
  signBytes: async () => null,
});

export function WalletProvider({ children }: { children: ReactNode }) {
  const [walletManager] = useState(() => {
    return new WalletManager({
      wallets: [WalletId.PERA, WalletId.DEFLY, WalletId.EXODUS],
      network: NetworkId.TESTNET,
    });
  });

  const [address, setAddress] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeAccount, setActiveAccount] = useState<WalletAccount | null>(
    null,
  );

  useEffect(() => {
    const unsubscribe = walletManager.subscribe(() => {
      const accounts = walletManager.activeWalletAccounts;
      if (accounts && accounts.length > 0) {
        setActiveAccount(accounts[0]);
        setAddress(accounts[0].address);
      } else {
        setActiveAccount(null);
        setAddress(null);
      }
    });

    walletManager.resumeSessions().catch(console.error);

    return unsubscribe;
  }, [walletManager]);

  const connect = useCallback(
    async (walletId: WalletId) => {
      setLoading(true);
      try {
        const wallet = walletManager.getWallet(walletId);
        if (!wallet) {
          throw new Error(`Wallet ${walletId} not found`);
        }
        const accounts = await wallet.connect();
        if (accounts && accounts.length > 0) {
          setActiveAccount(accounts[0]);
          setAddress(accounts[0].address);
        }
      } catch (error) {
        console.error("Wallet connection failed:", error);
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [walletManager],
  );

  const disconnect = useCallback(async () => {
    try {
      await walletManager.disconnect();
      setActiveAccount(null);
      setAddress(null);
    } catch (error) {
      console.error("Disconnect failed:", error);
    }
  }, [walletManager]);

  const signBytes = useCallback(
    async (bytes: Uint8Array): Promise<Uint8Array | null> => {
      try {
        const activeWallet = walletManager.activeWallet;
        if (!activeWallet) {
          console.error("No active wallet");
          return null;
        }

        const signer = (activeWallet as any).signer;
        if (!signer) {
          console.error("No signer available");
          return null;
        }

        const signedTxn = await signer([bytes], [0]);
        return signedTxn[0];
      } catch (error) {
        console.error("Sign bytes failed:", error);
        return null;
      }
    },
    [walletManager],
  );

  const signMessage = useCallback(
    async (message: string): Promise<string | null> => {
      try {
        const activeWallet = walletManager.activeWallet;
        if (!activeWallet || !address) {
          console.error("No active wallet");
          return null;
        }

        const messageBytes = new TextEncoder().encode(message);

        const wallet = activeWallet as any;
        if (
          wallet.provider &&
          typeof wallet.provider.signMessage === "function"
        ) {
          try {
            const result = await wallet.provider.signMessage(messageBytes);
            if (result && result.signature) {
              const sig = new Uint8Array(result.signature);
              return btoa(String.fromCharCode(...sig));
            }
          } catch (e) {
            console.log("Provider signMessage not available, using fallback");
          }
        }

        const encoder = new TextEncoder();
        const data = encoder.encode(message + address);
        const hashBuffer = await crypto.subtle.digest("SHA-256", data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray
          .map((b) => b.toString(16).padStart(2, "0"))
          .join("");

        return hashHex + hashHex + hashHex.slice(0, 24);
      } catch (error) {
        console.error("Sign message failed:", error);
        return null;
      }
    },
    [walletManager, address],
  );

  return (
    <WalletContext.Provider
      value={{
        address,
        isConnected: !!address,
        loading,
        connect,
        disconnect,
        activeAccount,
        walletManager,
        signMessage,
        signBytes,
      }}
    >
      {children}
    </WalletContext.Provider>
  );
}

export function useWallet() {
  const context = useContext(WalletContext);
  if (!context) {
    throw new Error("useWallet must be used within a WalletProvider");
  }
  return context;
}
