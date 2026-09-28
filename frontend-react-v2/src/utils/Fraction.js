/**
 * Exact Rational Arithmetic Engine for Gaussian Elimination
 */

function gcd(a, b) {
  a = Math.abs(a);
  b = Math.abs(b);
  while (b) {
    const t = b;
    b = a % b;
    a = t;
  }
  return a;
}

export class Fraction {
  constructor(n, d = 1) {
    if (typeof n === 'string') {
      if (n.includes('/')) {
        const parts = n.split('/');
        n = parseInt(parts[0], 10);
        d = parseInt(parts[1], 10);
      } else {
        n = parseInt(n, 10);
        d = 1;
      }
    }
    if (d === 0) throw new Error('Division par zéro dans une fraction');
    if (d < 0) {
      n = -n;
      d = -d;
    }
    const g = gcd(n, d);
    this.n = n / g;
    this.d = d / g;
  }

  static from(val) {
    if (val instanceof Fraction) return val;
    return new Fraction(val);
  }

  add(other) {
    const o = Fraction.from(other);
    return new Fraction(this.n * o.d + o.n * this.d, this.d * o.d);
  }

  sub(other) {
    const o = Fraction.from(other);
    return new Fraction(this.n * o.d - o.n * this.d, this.d * o.d);
  }

  mul(other) {
    const o = Fraction.from(other);
    return new Fraction(this.n * o.n, this.d * o.d);
  }

  div(other) {
    const o = Fraction.from(other);
    if (o.n === 0) throw new Error('Division par zéro');
    return new Fraction(this.n * o.d, this.d * o.n);
  }

  equals(other) {
    const o = Fraction.from(other);
    return this.n === o.n && this.d === o.d;
  }

  isZero() {
    return this.n === 0;
  }

  toString() {
    if (this.d === 1) return `${this.n}`;
    return `${this.n}/${this.d}`;
  }

  toKaTeX() {
    if (this.d === 1) return `${this.n}`;
    if (this.n < 0) return `-\\frac{${-this.n}}{${this.d}}`;
    return `\\frac{${this.n}}{${this.d}}`;
  }
}
