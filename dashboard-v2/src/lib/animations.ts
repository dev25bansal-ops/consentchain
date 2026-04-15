import { Variants, Transition } from "framer-motion";

export const easing = {
  easeInOut: [0.4, 0, 0.2, 1] as const,
  easeOut: [0, 0, 0.2, 1] as const,
  easeIn: [0.4, 0, 1, 1] as const,
};

export const springConfig = {
  default: { type: "spring" as const, stiffness: 300, damping: 30 },
  bouncy: { type: "spring" as const, stiffness: 400, damping: 20 },
  stiff: { type: "spring" as const, stiffness: 500, damping: 35 },
};

export const transition: Transition = {
  duration: 0.3,
  ease: easing.easeInOut,
};

export const fastTransition: Transition = {
  duration: 0.15,
  ease: easing.easeOut,
};

export const slowTransition: Transition = {
  duration: 0.5,
  ease: easing.easeInOut,
};

export const fadeIn: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
};

export const fadeInUp: Variants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
};

export const fadeInDown: Variants = {
  initial: { opacity: 0, y: -20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: 10 },
};

export const fadeInLeft: Variants = {
  initial: { opacity: 0, x: -20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: 10 },
};

export const fadeInRight: Variants = {
  initial: { opacity: 0, x: 20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -10 },
};

export const scaleIn: Variants = {
  initial: { opacity: 0, scale: 0.9 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.95 },
};

export const scaleInCenter: Variants = {
  initial: { opacity: 0, scale: 0.8 },
  animate: { opacity: 1, scale: 1, transition: springConfig.default },
  exit: { opacity: 0, scale: 0.8 },
};

export const slideInFromBottom: Variants = {
  initial: { opacity: 0, y: 50 },
  animate: { opacity: 1, y: 0, transition: springConfig.default },
  exit: { opacity: 0, y: 20 },
};

export const slideInFromTop: Variants = {
  initial: { opacity: 0, y: -50 },
  animate: { opacity: 1, y: 0, transition: springConfig.default },
  exit: { opacity: 0, y: -20 },
};

export const staggerContainer: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.1,
    },
  },
};

export const staggerContainerFast: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.04,
      delayChildren: 0.05,
    },
  },
};

export const staggerItem: Variants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: springConfig.default },
};

export const staggerItemScale: Variants = {
  initial: { opacity: 0, scale: 0.95 },
  animate: { opacity: 1, scale: 1, transition: springConfig.default },
};

export const pageTransition: Variants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
};

export const cardHover: Variants = {
  initial: { scale: 1, y: 0 },
  hover: {
    scale: 1.02,
    y: -4,
    transition: { duration: 0.2, ease: easing.easeOut },
  },
  tap: { scale: 0.98 },
};

export const buttonHover: Variants = {
  initial: { scale: 1 },
  hover: { scale: 1.02, transition: fastTransition },
  tap: { scale: 0.98 },
};

export const listVariants: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.05,
    },
  },
};

export const listItemVariants: Variants = {
  initial: { opacity: 0, x: -20 },
  animate: { opacity: 1, x: 0, transition: springConfig.default },
};

export const accordionVariants: Variants = {
  initial: { height: 0, opacity: 0 },
  animate: { height: "auto", opacity: 1 },
  exit: { height: 0, opacity: 0 },
};

export const modalBackdrop: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
};

export const modalContent: Variants = {
  initial: { opacity: 0, scale: 0.95, y: 20 },
  animate: { opacity: 1, scale: 1, y: 0, transition: springConfig.default },
  exit: { opacity: 0, scale: 0.95, y: 20 },
};

export const tooltipVariants: Variants = {
  initial: { opacity: 0, scale: 0.9 },
  animate: { opacity: 1, scale: 1, transition: fastTransition },
  exit: { opacity: 0, scale: 0.9 },
};

export const pulseVariants: Variants = {
  initial: { scale: 1 },
  animate: {
    scale: [1, 1.05, 1],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: "easeInOut",
    },
  },
};

export const floatVariants: Variants = {
  initial: { y: 0 },
  animate: {
    y: [-5, 5, -5],
    transition: {
      duration: 3,
      repeat: Infinity,
      ease: "easeInOut",
    },
  },
};

export const shimmerVariants: Variants = {
  initial: { backgroundPosition: "200% 0" },
  animate: {
    backgroundPosition: "-200% 0",
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: "linear",
    },
  },
};

export const createStaggeredDelay = (
  index: number,
  baseDelay: number = 0.05,
): number => {
  return index * baseDelay;
};

export const getAnimationDelay = (
  delay: number,
): { transition: { delay: number } } => ({
  transition: { delay },
});

export const springTransition = (
  stiffness: number = 300,
  damping: number = 30,
): Transition => ({
  type: "spring",
  stiffness,
  damping,
});
