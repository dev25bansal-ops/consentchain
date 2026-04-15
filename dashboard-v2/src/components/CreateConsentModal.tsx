import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Shield,
  Calendar,
  Database,
  Building2,
  AlertCircle,
  Check,
  Loader2,
} from "lucide-react";
import { useWallet } from "../hooks/useWallet";
import api from "../lib/api";

interface Fiduciary {
  id: string;
  name: string;
  registration_number: string;
  data_categories: string[];
  purposes: string[];
}

interface CreateConsentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const DATA_TYPES = [
  { value: "NAME", label: "Full Name" },
  { value: "EMAIL", label: "Email Address" },
  { value: "PHONE", label: "Phone Number" },
  { value: "ADDRESS", label: "Physical Address" },
  { value: "AADHAAR", label: "Aadhaar Number" },
  { value: "PAN", label: "PAN Number" },
  { value: "FINANCIAL", label: "Financial Data" },
  { value: "HEALTH", label: "Health Records" },
  { value: "LOCATION", label: "Location Data" },
  { value: "BIOMETRIC", label: "Biometric Data" },
  { value: "EDUCATION", label: "Education Records" },
  { value: "EMPLOYMENT", label: "Employment History" },
];

const PURPOSES = [
  "Account Registration",
  "Service Delivery",
  "Payment Processing",
  "KYC Verification",
  "Marketing Communications",
  "Analytics & Research",
  "Fraud Prevention",
  "Legal Compliance",
  "Healthcare Services",
  "Financial Services",
];

export default function CreateConsentModal({
  isOpen,
  onClose,
  onSuccess,
}: CreateConsentModalProps) {
  const { address } = useWallet();
  const [fiduciaries, setFiduciaries] = useState<Fiduciary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState(1);

  const [formData, setFormData] = useState({
    fiduciary_id: "",
    purpose: "",
    customPurpose: "",
    data_types: [] as string[],
    duration_days: 30,
  });

  useEffect(() => {
    if (isOpen) {
      loadFiduciaries();
    }
  }, [isOpen]);

  async function loadFiduciaries() {
    try {
      const response = await api.get("/api/v1/public/fiduciaries");
      setFiduciaries(response.data?.data?.fiduciaries || []);
    } catch (err) {
      console.error("Failed to load fiduciaries:", err);
    }
  }

  function toggleDataType(type: string) {
    setFormData((prev) => ({
      ...prev,
      data_types: prev.data_types.includes(type)
        ? prev.data_types.filter((t) => t !== type)
        : [...prev.data_types, type],
    }));
  }

  async function handleSubmit() {
    if (!address) {
      setError("Please connect your wallet first");
      return;
    }

    if (!formData.fiduciary_id) {
      setError("Please select a fiduciary");
      return;
    }

    if (!formData.purpose && !formData.customPurpose) {
      setError("Please select or enter a purpose");
      return;
    }

    if (formData.data_types.length === 0) {
      setError("Please select at least one data type");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const consentData = {
        principal_wallet: address,
        fiduciary_id: formData.fiduciary_id,
        purpose: formData.customPurpose || formData.purpose,
        data_types: formData.data_types,
        duration_days: formData.duration_days,
        signature: "wallet_signature_placeholder",
      };

      const response = await api.post(
        "/api/v1/public/consent/create",
        consentData,
      );

      if (response.data.success) {
        setStep(3);
        setTimeout(() => {
          onSuccess();
          onClose();
          resetForm();
        }, 2000);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create consent");
    } finally {
      setLoading(false);
    }
  }

  function resetForm() {
    setFormData({
      fiduciary_id: "",
      purpose: "",
      customPurpose: "",
      data_types: [],
      duration_days: 30,
    });
    setStep(1);
    setError(null);
  }

  function handleClose() {
    onClose();
    setTimeout(resetForm, 300);
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          style={styles.overlay}
          onClick={handleClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            style={styles.modal}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={styles.header}>
              <div style={styles.headerIcon}>
                <Shield size={24} color="#7c3aed" />
              </div>
              <div>
                <h2 style={styles.title}>Grant New Consent</h2>
                <p style={styles.subtitle}>
                  Authorise a data fiduciary to process your personal data
                </p>
              </div>
              <motion.button
                onClick={handleClose}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                style={styles.closeBtn}
              >
                <X size={18} />
              </motion.button>
            </div>

            <div style={styles.steps}>
              {[1, 2, 3].map((s) => (
                <div key={s} style={styles.step}>
                  <motion.div
                    animate={{
                      background:
                        step >= s
                          ? "linear-gradient(135deg, #7c3aed, #9333ea)"
                          : "rgba(255,255,255,0.1)",
                    }}
                    style={styles.stepNum}
                  >
                    {step > s ? <Check size={12} /> : s}
                  </motion.div>
                  <span
                    style={{
                      ...styles.stepLabel,
                      color: step >= s ? "#a78bfa" : "#5a5480",
                    }}
                  >
                    {s === 1 ? "Fiduciary" : s === 2 ? "Details" : "Review"}
                  </span>
                </div>
              ))}
            </div>

            <div style={styles.content}>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  style={styles.errorBox}
                >
                  <AlertCircle size={16} />
                  {error}
                </motion.div>
              )}

              {step === 1 && (
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  style={styles.stepContent}
                >
                  <label style={styles.label}>
                    <Building2 size={14} />
                    Select Data Fiduciary
                  </label>
                  <div style={styles.fiduciaryList}>
                    {fiduciaries.length === 0 ? (
                      <div style={styles.emptyFiduciary}>
                        No active fiduciaries available
                      </div>
                    ) : (
                      fiduciaries.map((f) => (
                        <motion.div
                          key={f.id}
                          onClick={() =>
                            setFormData((prev) => ({
                              ...prev,
                              fiduciary_id: f.id,
                            }))
                          }
                          whileHover={{ scale: 1.01 }}
                          style={{
                            ...styles.fiduciaryCard,
                            ...(formData.fiduciary_id === f.id
                              ? styles.fiduciaryCardActive
                              : {}),
                          }}
                        >
                          <div style={styles.fiduciaryName}>{f.name}</div>
                          <div style={styles.fiduciaryReg}>
                            {f.registration_number}
                          </div>
                          <div style={styles.fiduciaryCats}>
                            {f.data_categories?.slice(0, 3).map((cat) => (
                              <span key={cat} style={styles.catTag}>
                                {cat}
                              </span>
                            ))}
                          </div>
                        </motion.div>
                      ))
                    )}
                  </div>
                </motion.div>
              )}

              {step === 2 && (
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  style={styles.stepContent}
                >
                  <label style={styles.label}>
                    <Database size={14} />
                    Purpose of Consent
                  </label>
                  <div style={styles.purposeGrid}>
                    {PURPOSES.map((p) => (
                      <motion.div
                        key={p}
                        onClick={() =>
                          setFormData((prev) => ({
                            ...prev,
                            purpose: p,
                            customPurpose: "",
                          }))
                        }
                        whileHover={{ scale: 1.02 }}
                        style={{
                          ...styles.purposeChip,
                          ...(formData.purpose === p
                            ? styles.purposeChipActive
                            : {}),
                        }}
                      >
                        {p}
                      </motion.div>
                    ))}
                  </div>
                  <input
                    type="text"
                    placeholder="Or enter custom purpose..."
                    value={formData.customPurpose}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        customPurpose: e.target.value,
                        purpose: "",
                      }))
                    }
                    style={styles.customInput}
                  />

                  <label style={{ ...styles.label, marginTop: 24 }}>
                    <Database size={14} />
                    Data Types to Share
                  </label>
                  <div style={styles.dataTypesGrid}>
                    {DATA_TYPES.map((type) => (
                      <motion.div
                        key={type.value}
                        onClick={() => toggleDataType(type.value)}
                        whileHover={{ scale: 1.02 }}
                        style={{
                          ...styles.dataTypeChip,
                          ...(formData.data_types.includes(type.value)
                            ? styles.dataTypeChipActive
                            : {}),
                        }}
                      >
                        {formData.data_types.includes(type.value) && (
                          <Check size={12} />
                        )}
                        {type.label}
                      </motion.div>
                    ))}
                  </div>

                  <label style={{ ...styles.label, marginTop: 24 }}>
                    <Calendar size={14} />
                    Consent Duration: {formData.duration_days} days
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="365"
                    value={formData.duration_days}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        duration_days: parseInt(e.target.value),
                      }))
                    }
                    style={styles.slider}
                  />
                  <div style={styles.durationLabels}>
                    <span>1 day</span>
                    <span>1 year</span>
                  </div>
                </motion.div>
              )}

              {step === 3 && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  style={styles.successContent}
                >
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", delay: 0.2 }}
                    style={styles.successIcon}
                  >
                    <Check size={40} />
                  </motion.div>
                  <h3 style={styles.successTitle}>Consent Granted!</h3>
                  <p style={styles.successText}>
                    Your consent has been recorded on the Algorand blockchain.
                    You can view it in your dashboard.
                  </p>
                </motion.div>
              )}
            </div>

            <div style={styles.footer}>
              {step < 3 && (
                <>
                  {step > 1 && (
                    <motion.button
                      onClick={() => setStep(step - 1)}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      style={styles.backBtn}
                    >
                      Back
                    </motion.button>
                  )}
                  <motion.button
                    onClick={() => {
                      if (step === 1 && !formData.fiduciary_id) {
                        setError("Please select a fiduciary");
                        return;
                      }
                      if (step === 2) {
                        handleSubmit();
                      } else {
                        setStep(step + 1);
                      }
                    }}
                    disabled={loading}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    style={styles.nextBtn}
                  >
                    {loading ? (
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{
                          duration: 1,
                          repeat: Infinity,
                          ease: "linear",
                        }}
                      >
                        <Loader2 size={16} />
                      </motion.div>
                    ) : step === 2 ? (
                      "Grant Consent"
                    ) : (
                      "Continue"
                    )}
                  </motion.button>
                </>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(11,9,23,0.85)",
    backdropFilter: "blur(8px)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
    padding: 20,
  },
  modal: {
    background: "linear-gradient(180deg, #1a1429 0%, #0b0917 100%)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 24,
    width: "100%",
    maxWidth: 520,
    maxHeight: "90vh",
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
  },
  header: {
    display: "flex",
    alignItems: "flex-start",
    gap: 16,
    padding: "24px 24px 16px",
    borderBottom: "1px solid rgba(255,255,255,0.05)",
  },
  headerIcon: {
    width: 48,
    height: 48,
    borderRadius: 14,
    background: "rgba(124,58,237,0.1)",
    border: "1px solid rgba(124,58,237,0.2)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  title: {
    fontFamily: "'Syne', sans-serif",
    fontSize: 20,
    fontWeight: 700,
    color: "#ede9ff",
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 12,
    color: "#5a5480",
  },
  closeBtn: {
    marginLeft: "auto",
    padding: 8,
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 10,
    color: "#9d96c8",
    cursor: "pointer",
  },
  steps: {
    display: "flex",
    justifyContent: "center",
    gap: 32,
    padding: "16px 24px",
    borderBottom: "1px solid rgba(255,255,255,0.05)",
  },
  step: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 6,
  },
  stepNum: {
    width: 28,
    height: 28,
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 12,
    fontWeight: 600,
    color: "white",
  },
  stepLabel: {
    fontSize: 11,
    fontWeight: 500,
  },
  content: {
    flex: 1,
    overflow: "auto",
    padding: 24,
  },
  errorBox: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: 12,
    background: "rgba(244,63,94,0.1)",
    border: "1px solid rgba(244,63,94,0.2)",
    borderRadius: 10,
    color: "#fb7185",
    fontSize: 13,
    marginBottom: 16,
  },
  stepContent: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  label: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    fontSize: 13,
    fontWeight: 600,
    color: "#ede9ff",
    marginBottom: 8,
  },
  fiduciaryList: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
    maxHeight: 240,
    overflow: "auto",
  },
  fiduciaryCard: {
    padding: 12,
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 12,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  fiduciaryCardActive: {
    background: "rgba(124,58,237,0.1)",
    borderColor: "rgba(124,58,237,0.3)",
  },
  fiduciaryName: {
    fontWeight: 600,
    color: "#ede9ff",
    marginBottom: 2,
  },
  fiduciaryReg: {
    fontSize: 11,
    color: "#5a5480",
    marginBottom: 8,
  },
  fiduciaryCats: {
    display: "flex",
    gap: 4,
    flexWrap: "wrap",
  },
  catTag: {
    padding: "2px 6px",
    background: "rgba(255,255,255,0.05)",
    borderRadius: 4,
    fontSize: 10,
    color: "#9d96c8",
  },
  emptyFiduciary: {
    padding: 40,
    textAlign: "center",
    color: "#5a5480",
  },
  purposeGrid: {
    display: "flex",
    flexWrap: "wrap",
    gap: 6,
    marginBottom: 12,
  },
  purposeChip: {
    padding: "6px 12px",
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 100,
    fontSize: 12,
    color: "#9d96c8",
    cursor: "pointer",
    transition: "all 0.2s",
  },
  purposeChipActive: {
    background: "rgba(124,58,237,0.15)",
    borderColor: "rgba(124,58,237,0.3)",
    color: "#a78bfa",
  },
  customInput: {
    width: "100%",
    padding: 12,
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 10,
    color: "#ede9ff",
    fontSize: 13,
    outline: "none",
  },
  dataTypesGrid: {
    display: "flex",
    flexWrap: "wrap",
    gap: 6,
  },
  dataTypeChip: {
    display: "flex",
    alignItems: "center",
    gap: 4,
    padding: "6px 10px",
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 8,
    fontSize: 11,
    color: "#9d96c8",
    cursor: "pointer",
    transition: "all 0.2s",
  },
  dataTypeChipActive: {
    background: "rgba(16,185,129,0.1)",
    borderColor: "rgba(16,185,129,0.3)",
    color: "#34d399",
  },
  slider: {
    width: "100%",
    height: 6,
    borderRadius: 100,
    background: "rgba(255,255,255,0.1)",
    outline: "none",
    cursor: "pointer",
  },
  durationLabels: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: 10,
    color: "#5a5480",
    marginTop: 4,
  },
  successContent: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: "40px 20px",
    textAlign: "center",
  },
  successIcon: {
    width: 80,
    height: 80,
    borderRadius: "50%",
    background: "linear-gradient(135deg, #10b981, #34d399)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "white",
    marginBottom: 20,
  },
  successTitle: {
    fontFamily: "'Syne', sans-serif",
    fontSize: 22,
    fontWeight: 700,
    color: "#ede9ff",
    marginBottom: 8,
  },
  successText: {
    fontSize: 13,
    color: "#5a5480",
    maxWidth: 280,
    lineHeight: 1.6,
  },
  footer: {
    display: "flex",
    gap: 8,
    padding: "16px 24px",
    borderTop: "1px solid rgba(255,255,255,0.05)",
  },
  backBtn: {
    padding: "12px 20px",
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 10,
    color: "#9d96c8",
    fontWeight: 600,
    fontSize: 13,
    cursor: "pointer",
  },
  nextBtn: {
    flex: 1,
    padding: "12px 20px",
    background: "linear-gradient(135deg, #7c3aed, #9333ea)",
    border: "none",
    borderRadius: 10,
    color: "white",
    fontWeight: 600,
    fontSize: 13,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
};
