import React, { useState } from 'react';

/**
 * Composant d'image responsive optimisé pour les illustrations MikaMike.
 * - Charge d'abord l'URL distante sur mikamike.fr
 * - Bascule automatiquement sur le fallback local en cas de problème réseau
 * - Garantit zéro déformation (object-fit / aspect-ratio)
 * - Supporte le chargement différé (loading="lazy", decoding="async")
 * - Animation fluide au survol
 */
export default function ResponsiveIllustration({
  media,
  altOverride,
  className = '',
  style = {},
  aspectRatio = '16/9',
  objectFit = 'cover',
  maxHeight,
  onClick
}) {
  const [imgSrc, setImgSrc] = useState(media?.remoteUrl || media?.localUrl || '');
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);

  const handleImgError = () => {
    if (imgSrc !== media?.localUrl && media?.localUrl) {
      // Retry with local fallback
      setImgSrc(media.localUrl);
    } else {
      setHasError(true);
    }
  };

  const altText = altOverride || media?.alt || media?.title || 'Illustration MikaMike';

  return (
    <div
      className={`illustration-wrapper ${className}`}
      style={{
        position: 'relative',
        width: '100%',
        aspectRatio: aspectRatio,
        maxHeight: maxHeight || 'none',
        borderRadius: '12px',
        overflow: 'hidden',
        background: '#1e293b',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
        cursor: onClick ? 'pointer' : 'default',
        ...style
      }}
      onClick={onClick}
    >
      {/* Loading Skeleton */}
      {!isLoaded && !hasError && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%)',
            backgroundSize: '200% 100%',
            animation: 'shimmer 1.8s infinite'
          }}
        />
      )}

      {/* Main Responsive Image */}
      {!hasError ? (
        <img
          src={imgSrc}
          alt={altText}
          loading="lazy"
          decoding="async"
          onLoad={() => setIsLoaded(true)}
          onError={handleImgError}
          style={{
            width: '100%',
            height: '100%',
            objectFit: objectFit,
            objectPosition: 'center',
            opacity: isLoaded ? 1 : 0,
            transition: 'opacity 0.4s ease, transform 0.3s ease',
            display: 'block'
          }}
          className="responsive-illustration-img"
        />
      ) : (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: '#94a3b8',
            fontSize: '0.85rem',
            padding: '1rem',
            textAlign: 'center'
          }}
        >
          🖼️ {media?.title || 'Illustration MikaMike'}
        </div>
      )}

      {/* Badge Tag ID if hovered/debug */}
      {media?.id && (
        <div
          style={{
            position: 'absolute',
            bottom: '8px',
            right: '8px',
            background: 'rgba(15, 23, 42, 0.85)',
            backdropFilter: 'blur(6px)',
            color: '#34d399',
            fontSize: '0.65rem',
            fontWeight: '700',
            padding: '2px 8px',
            borderRadius: '6px',
            border: '1px solid rgba(52, 211, 153, 0.4)',
            pointerEvents: 'none',
            letterSpacing: '0.05em'
          }}
        >
          WP ID #{media.id}
        </div>
      )}
    </div>
  );
}
