import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';
const variants = cva('button', { variants: { variant: { default: 'button-default', ghost: 'button-ghost', outline: 'button-outline' }, size: { default: '', icon: 'button-icon' } }, defaultVariants: { variant: 'default', size: 'default' } });
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof variants> { asChild?: boolean }
export function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) { const Comp = asChild ? Slot : 'button'; return <Comp className={cn(variants({variant, size}), className)} {...props}/>; }
