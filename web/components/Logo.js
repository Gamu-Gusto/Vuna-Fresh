import Image from 'next/image';

// Cropped wordmark (the original logo files are padded squares, which made
// every header ~176px tall). `dark` is the white-and-green version for navy.
export default function Logo({ dark = true, className = 'h-7 w-auto' }) {
  return (
    <Image
      src={dark ? '/vunafresh-wordmark-dark.png' : '/vunafresh-wordmark.png'}
      alt="Vuna Fresh"
      width={1102}
      height={272}
      className={className}
      priority
    />
  );
}
