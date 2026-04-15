// Reusable UI Component Library
// Production-ready components with proper TypeScript, accessibility, and styling

import React, { forwardRef } from "react";
import type {
  ButtonProps,
  CardProps,
  BadgeProps,
  InputProps,
  SelectProps,
  ToggleSwitchProps,
  StatCardProps,
} from "../../types";
import {
  colors,
  shadows,
  transitions,
  borderRadius,
  typography,
  CONSENT_STATUS_CONFIG,
} from "../../lib/design-tokens";

// ==================== Button Component ====================
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      isLoading = false,
      disabled = false,
      fullWidth = false,
      leftIcon,
      rightIcon,
      children,
      onClick,
      type = "button",
      className = "",
      "aria-label": ariaLabel,
    },
    ref,
  ) => {
    const baseStyles: React.CSSProperties = {
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      gap: "0.5rem",
      fontWeight: typography.fontWeight.semibold,
      borderRadius: borderRadius.lg,
      cursor: disabled || isLoading ? "not-allowed" : "pointer",
      opacity: disabled || isLoading ? 0.6 : 1,
      transition: `all ${transitions.normal}`,
      width: fullWidth ? "100%" : "auto",
      outline: "none",
      border: "none",
    };

    const sizeStyles: Record<string, React.CSSProperties> = {
      sm: { padding: "0.5rem 1rem", fontSize: typography.fontSize.sm },
      md: { padding: "0.75rem 1.5rem", fontSize: typography.fontSize.base },
      lg: { padding: "1rem 2rem", fontSize: typography.fontSize.lg },
    };

    const variantStyles: Record<string, React.CSSProperties> = {
      primary: {
        background: `linear-gradient(135deg, ${colors.primary[600]} 0%, ${colors.primary[700]} 100%)`,
        color: "white",
        boxShadow: shadows.md,
      },
      secondary: {
        background: "white",
        color: colors.neutral[700],
        border: `2px solid ${colors.neutral[200]}`,
      },
      ghost: {
        background: "transparent",
        color: colors.neutral[600],
      },
      danger: {
        background: colors.error.light,
        color: colors.error.dark,
      },
    };

    const handleMouseEnter = (e: React.MouseEvent<HTMLButtonElement>) => {
      if (!disabled && !isLoading) {
        e.currentTarget.style.transform = "translateY(-2px)";
        if (variant === "primary") {
          e.currentTarget.style.boxShadow = shadows.lg;
        }
      }
    };

    const handleMouseLeave = (e: React.MouseEvent<HTMLButtonElement>) => {
      e.currentTarget.style.transform = "translateY(0)";
      if (variant === "primary") {
        e.currentTarget.style.boxShadow = shadows.md;
      }
    };

    return (
      <button
        ref={ref}
        type={type}
        onClick={onClick}
        disabled={disabled || isLoading}
        aria-label={ariaLabel}
        aria-busy={isLoading}
        className={className}
        style={{
          ...baseStyles,
          ...sizeStyles[size],
          ...variantStyles[variant],
        }}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {isLoading ? (
          <>
            <Spinner size={size === "sm" ? 16 : 20} />
            Loading...
          </>
        ) : (
          <>
            {leftIcon}
            {children}
            {rightIcon}
          </>
        )}
      </button>
    );
  },
);

Button.displayName = "Button";

// ==================== Card Component ====================
export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      children,
      className = "",
      style,
      onClick,
      interactive = false,
      padding = "md",
      shadow = "sm",
    },
    ref,
  ) => {
    const paddingStyles: Record<string, string> = {
      none: "0",
      sm: "1rem",
      md: "1.5rem",
      lg: "2rem",
    };

    const shadowStyles: Record<string, string> = {
      none: "none",
      sm: shadows.sm,
      md: shadows.md,
      lg: shadows.lg,
    };

    return (
      <div
        ref={ref}
        onClick={onClick}
        className={className}
        style={{
          background: "white",
          borderRadius: borderRadius.xl,
          boxShadow: shadowStyles[shadow],
          border: `1px solid ${colors.neutral[100]}`,
          padding: paddingStyles[padding],
          transition: `all ${transitions.normal}`,
          cursor: interactive ? "pointer" : "default",
          ...style,
        }}
        role={interactive ? "button" : undefined}
        tabIndex={interactive ? 0 : undefined}
      >
        {children}
      </div>
    );
  },
);

Card.displayName = "Card";

// ==================== Badge Component ====================
export const Badge: React.FC<BadgeProps> = ({ status, size = "sm" }) => {
  const config = CONSENT_STATUS_CONFIG[status] || CONSENT_STATUS_CONFIG.PENDING;

  const sizeStyles: Record<string, React.CSSProperties> = {
    sm: { padding: "0.25rem 0.625rem", fontSize: "0.7rem" },
    md: { padding: "0.375rem 0.75rem", fontSize: "0.75rem" },
  };

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.375rem",
        borderRadius: borderRadius.full,
        fontWeight: typography.fontWeight.semibold,
        letterSpacing: "0.025em",
        background: config.bgColor,
        color: config.textColor,
        ...sizeStyles[size],
      }}
      role="status"
      aria-label={`Status: ${config.label}`}
    >
      <span
        style={{
          width: size === "sm" ? "5px" : "6px",
          height: size === "sm" ? "5px" : "6px",
          background: config.color,
          borderRadius: "50%",
        }}
      />
      {config.label}
    </span>
  );
};

// ==================== Input Component ====================
export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      type = "text",
      placeholder,
      value,
      onChange,
      error,
      disabled = false,
      leftIcon,
      rightIcon,
      label,
      id,
      name,
      required = false,
    },
    ref,
  ) => {
    const inputId =
      id || name || `input-${Math.random().toString(36).substr(2, 9)}`;

    return (
      <div style={{ width: "100%" }}>
        {label && (
          <label
            htmlFor={inputId}
            style={{
              display: "block",
              fontSize: typography.fontSize.sm,
              fontWeight: typography.fontWeight.medium,
              color: colors.neutral[700],
              marginBottom: "0.375rem",
            }}
          >
            {label}
            {required && <span style={{ color: colors.error.main }}> *</span>}
          </label>
        )}
        <div style={{ position: "relative" }}>
          {leftIcon && (
            <span
              style={{
                position: "absolute",
                left: "0.75rem",
                top: "50%",
                transform: "translateY(-50%)",
                color: colors.neutral[400],
              }}
            >
              {leftIcon}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            name={name}
            type={type}
            placeholder={placeholder}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            required={required}
            aria-invalid={!!error}
            aria-describedby={error ? `${inputId}-error` : undefined}
            style={{
              width: "100%",
              padding: leftIcon
                ? "0.75rem 1rem 0.75rem 2.5rem"
                : "0.75rem 1rem",
              border: `2px solid ${error ? colors.error.main : colors.neutral[200]}`,
              borderRadius: borderRadius.lg,
              fontSize: typography.fontSize.base,
              outline: "none",
              transition: `all ${transitions.normal}`,
              background: disabled ? colors.neutral[50] : "white",
              cursor: disabled ? "not-allowed" : "text",
            }}
          />
          {rightIcon && (
            <span
              style={{
                position: "absolute",
                right: "0.75rem",
                top: "50%",
                transform: "translateY(-50%)",
                color: colors.neutral[400],
              }}
            >
              {rightIcon}
            </span>
          )}
        </div>
        {error && (
          <p
            id={`${inputId}-error`}
            role="alert"
            style={{
              fontSize: typography.fontSize.sm,
              color: colors.error.main,
              marginTop: "0.375rem",
            }}
          >
            {error}
          </p>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";

// ==================== Select Component ====================
export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      options,
      value,
      onChange,
      placeholder,
      disabled = false,
      label,
      id,
      name,
      error,
    },
    ref,
  ) => {
    const selectId =
      id || name || `select-${Math.random().toString(36).substr(2, 9)}`;

    return (
      <div style={{ width: "100%" }}>
        {label && (
          <label
            htmlFor={selectId}
            style={{
              display: "block",
              fontSize: typography.fontSize.sm,
              fontWeight: typography.fontWeight.medium,
              color: colors.neutral[700],
              marginBottom: "0.375rem",
            }}
          >
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          name={name}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          aria-invalid={!!error}
          aria-describedby={error ? `${selectId}-error` : undefined}
          style={{
            width: "100%",
            padding: "0.75rem 1rem",
            border: `2px solid ${error ? colors.error.main : colors.neutral[200]}`,
            borderRadius: borderRadius.lg,
            fontSize: typography.fontSize.base,
            outline: "none",
            transition: `all ${transitions.normal}`,
            background: disabled ? colors.neutral[50] : "white",
            cursor: disabled ? "not-allowed" : "pointer",
          }}
        >
          {placeholder && <option value="">{placeholder}</option>}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {error && (
          <p
            id={`${selectId}-error`}
            role="alert"
            style={{
              fontSize: typography.fontSize.sm,
              color: colors.error.main,
              marginTop: "0.375rem",
            }}
          >
            {error}
          </p>
        )}
      </div>
    );
  },
);

Select.displayName = "Select";

// ==================== ToggleSwitch Component ====================
export const ToggleSwitch: React.FC<ToggleSwitchProps> = ({
  label,
  description,
  checked,
  onChange,
  disabled = false,
}) => {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => !disabled && onChange(!checked)}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0.75rem",
        background: disabled ? colors.neutral[50] : colors.neutral[50],
        borderRadius: borderRadius.lg,
        border: "none",
        cursor: disabled ? "not-allowed" : "pointer",
        width: "100%",
        transition: `all ${transitions.normal}`,
        textAlign: "left",
      }}
    >
      <div>
        <p
          style={{
            fontWeight: typography.fontWeight.medium,
            color: colors.neutral[700],
          }}
        >
          {label}
        </p>
        {description && (
          <p
            style={{
              fontSize: typography.fontSize.sm,
              color: colors.neutral[500],
            }}
          >
            {description}
          </p>
        )}
      </div>
      <div
        style={{
          width: "44px",
          height: "24px",
          background: checked ? colors.primary[600] : colors.neutral[300],
          borderRadius: borderRadius.full,
          position: "relative",
          transition: `background ${transitions.normal}`,
        }}
      >
        <div
          style={{
            position: "absolute",
            top: "2px",
            left: checked ? "22px" : "2px",
            width: "20px",
            height: "20px",
            background: "white",
            borderRadius: "50%",
            transition: `left ${transitions.normal}`,
            boxShadow: shadows.sm,
          }}
        />
      </div>
    </button>
  );
};

// ==================== StatCard Component ====================
export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon: Icon,
  trend,
  trendDirection = "neutral",
  color,
  delay = 0,
}) => {
  const colorMap = {
    primary: { bg: colors.primary[50], icon: colors.primary[600] },
    success: { bg: colors.success.light, icon: colors.success.main },
    warning: { bg: colors.warning.light, icon: colors.warning.main },
    error: { bg: colors.error.light, icon: colors.error.main },
    info: { bg: colors.info.light, icon: colors.info.main },
  };

  const trendColors = {
    up: { bg: colors.success.light, color: colors.success.dark },
    down: { bg: colors.error.light, color: colors.error.dark },
    neutral: { bg: colors.neutral[100], color: colors.neutral[600] },
  };

  return (
    <Card
      className="animate-slide-in-up"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
        }}
      >
        <div
          style={{
            width: "48px",
            height: "48px",
            background: colorMap[color].bg,
            borderRadius: borderRadius.lg,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Icon
            className=""
            style={{ width: 24, height: 24, color: colorMap[color].icon }}
          />
        </div>
        {trend && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.25rem",
              padding: "0.25rem 0.5rem",
              background: trendColors[trendDirection].bg,
              borderRadius: borderRadius.full,
              fontSize: typography.fontSize.xs,
              fontWeight: typography.fontWeight.medium,
              color: trendColors[trendDirection].color,
            }}
          >
            {trend}
          </div>
        )}
      </div>
      <div style={{ marginTop: "1rem" }}>
        <p
          style={{
            fontSize: typography.fontSize.sm,
            color: colors.neutral[500],
            marginBottom: "0.25rem",
          }}
        >
          {title}
        </p>
        <p
          style={{
            fontSize: typography.fontSize["2xl"],
            fontWeight: typography.fontWeight.bold,
            color: colors.neutral[900],
          }}
        >
          {value}
        </p>
      </div>
    </Card>
  );
};

// ==================== Spinner Component ====================
interface SpinnerProps {
  size?: number;
  color?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({ size = 24, color }) => {
  return (
    <div
      role="status"
      aria-label="Loading"
      style={{
        width: size,
        height: size,
        border: `3px solid ${colors.neutral[200]}`,
        borderTopColor: color || colors.primary[500],
        borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
      }}
    />
  );
};

// ==================== Skeleton Component ====================
interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width = "100%",
  height = "1rem",
  borderRadius = "0.5rem",
}) => {
  return (
    <div
      style={{
        width: typeof width === "number" ? `${width}px` : width,
        height: typeof height === "number" ? `${height}px` : height,
        borderRadius,
        background: `linear-gradient(90deg, ${colors.neutral[200]} 25%, ${colors.neutral[100]} 50%, ${colors.neutral[200]} 75%)`,
        backgroundSize: "200% 100%",
        animation: "shimmer 1.5s infinite",
      }}
    />
  );
};
