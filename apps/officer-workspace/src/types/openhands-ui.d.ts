/**
 * Type declarations for @openhands/ui — temporary shim until the package
 * is built with bun (packages/openhands-ui/dist/).
 *
 * Source of truth: packages/openhands-ui/index.ts and individual component files.
 * DO NOT edit packages/openhands-ui/ — this is a local read-only declaration.
 */

declare module '@openhands/ui' {
  import type { ReactElement, HTMLProps, ReactNode } from 'react';

  // ── Button ──────────────────────────────────────────────────────
  type ComponentVariant = 'primary' | 'secondary' | 'tertiary';

  interface ButtonProps extends Omit<HTMLProps<HTMLButtonElement>, 'aria-disabled'> {
    size?: 'small' | 'large';
    variant?: ComponentVariant;
    start?: ReactElement<HTMLProps<SVGElement>>;
    end?: ReactElement<HTMLProps<SVGElement>>;
    testId?: string;
    disabled?: boolean;
    className?: string;
    children?: ReactNode;
  }

  export const Button: React.FC<ButtonProps>;

  // ── Typography ──────────────────────────────────────────────────
  interface TypographyBaseProps {
    testId?: string;
    className?: string;
  }

  interface HeadingProps extends TypographyBaseProps, HTMLProps<HTMLElement> {
    as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6' | 'span';
  }

  interface TextProps extends TypographyBaseProps, HTMLProps<HTMLElement> {
    fontSize?: 'xxs' | 'xs' | 's' | 'm' | 'l' | 'xl' | 'xxl' | 'xxxl';
    fontWeight?: 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900;
  }

  interface CodeProps extends TextProps {}

  export const Typography: {
    H1: React.FC<HeadingProps>;
    H2: React.FC<HeadingProps>;
    H3: React.FC<HeadingProps>;
    H4: React.FC<HeadingProps>;
    H5: React.FC<HeadingProps>;
    H6: React.FC<HeadingProps>;
    Text: React.FC<TextProps>;
    Code: React.FC<CodeProps>;
  };

  // ── Chip ────────────────────────────────────────────────────────
  type ChipColor =
    | 'primaryDark'
    | 'primaryLight'
    | 'green'
    | 'red'
    | 'aqua'
    | 'gray';

  type ChipVariant = 'pill' | 'corner';

  interface ChipProps extends HTMLProps<HTMLDivElement> {
    color?: ChipColor;
    variant?: ChipVariant;
    testId?: string;
    className?: string;
    children?: ReactNode;
  }

  export const Chip: React.FC<ChipProps>;

  // ── Input ───────────────────────────────────────────────────────
  interface InputProps extends Omit<HTMLProps<HTMLInputElement>, 'label' | 'aria-invalid' | 'checked'> {
    label: string;
    start?: ReactElement<HTMLProps<SVGElement>>;
    end?: ReactElement<HTMLProps<SVGElement>>;
    error?: string;
    hint?: string;
    testId?: string;
    id?: string;
    className?: string;
  }

  export const Input: React.FC<InputProps>;

  // ── Scrollable ──────────────────────────────────────────────────
  interface ScrollableProps extends HTMLProps<HTMLDivElement> {
    mode?: 'auto' | 'scroll';
    type?: 'horizontal' | 'vertical';
    tabIndex?: number;
    testId?: string;
    className?: string;
    children?: ReactNode;
  }

  export const Scrollable: React.FC<ScrollableProps>;

  // ── Tabs ────────────────────────────────────────────────────────
  interface TabsItemProps extends HTMLProps<HTMLDivElement> {
    text: string;
    icon?: string;
    children: ReactNode;
    testId?: string;
    className?: string;
  }

  interface TabsComponent extends React.FC<HTMLProps<HTMLDivElement> & { testId?: string }> {
    Item: React.FC<TabsItemProps>;
  }

  export const Tabs: TabsComponent;

  // ── Divider ─────────────────────────────────────────────────────
  export const Divider: React.FC<HTMLProps<HTMLDivElement> & { testId?: string }>;

  // ── Checkbox ────────────────────────────────────────────────────
  export const Checkbox: React.FC<HTMLProps<HTMLInputElement> & { testId?: string }>;

  // ── Dialog ──────────────────────────────────────────────────────
  interface DialogProps extends HTMLProps<HTMLDivElement> {
    open: boolean;
    onOpenChange: (value: boolean) => void;
    testId?: string;
    children?: ReactNode;
  }

  export const Dialog: React.FC<DialogProps>;

  // ── Icon ────────────────────────────────────────────────────────
  interface IconProps extends HTMLProps<SVGElement> {
    icon: string;
    testId?: string;
  }

  export const Icon: React.FC<IconProps>;

  // ── InteractiveChip ─────────────────────────────────────────────
  interface InteractiveChipProps extends HTMLProps<HTMLDivElement> {
    color?: ChipColor;
    variant?: ChipVariant;
    selected?: boolean;
    testId?: string;
    children?: ReactNode;
  }

  export const InteractiveChip: React.FC<InteractiveChipProps>;

  // ── RadioGroup / RadioOption ────────────────────────────────────
  export const RadioGroup: React.FC<HTMLProps<HTMLDivElement> & { testId?: string }>;
  export const RadioOption: React.FC<HTMLProps<HTMLDivElement> & { testId?: string }>;

  // ── Select ──────────────────────────────────────────────────────
  interface SelectProps extends HTMLProps<HTMLDivElement> {
    label?: string;
    testId?: string;
    children?: ReactNode;
  }

  export const Select: React.FC<SelectProps>;

  // ── Toggle ──────────────────────────────────────────────────────
  interface ToggleProps extends Omit<HTMLProps<HTMLButtonElement>, 'onChange'> {
    checked?: boolean;
    onChange?: (checked: boolean) => void;
    testId?: string;
  }

  export const Toggle: React.FC<ToggleProps>;

  // ── Tooltip ─────────────────────────────────────────────────────
  interface TooltipProps {
    content: ReactNode;
    children: ReactElement;
    testId?: string;
  }

  export const Tooltip: React.FC<TooltipProps>;

  // ── ToastManager ────────────────────────────────────────────────
  export const ToastManager: React.FC<HTMLProps<HTMLDivElement> & { children?: ReactNode }>;
  export const toasterMessages: Record<string, unknown>;
}
