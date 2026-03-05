// ============================================================
// 🪝 REACT HOOKS COLLECTION — 15 Production-Ready Hooks
// DevVault Pro 2026 — This alone saves you 20+ hours
// ============================================================
// Copy any hook into your project. Zero dependencies (except React).
// All hooks are TypeScript-ready with full type safety.
// ============================================================

// ─────────────────────────────────────────────
// 1. useLocalStorage — Persist state to localStorage
// ─────────────────────────────────────────────
function useLocalStorage<T>(key: string, initialValue: T) {
    const [storedValue, setStoredValue] = useState<T>(() => {
        if (typeof window === 'undefined') return initialValue;
        try {
            const item = window.localStorage.getItem(key);
            return item ? JSON.parse(item) : initialValue;
        } catch { return initialValue; }
    });

    const setValue = (value: T | ((val: T) => T)) => {
        const valueToStore = value instanceof Function ? value(storedValue) : value;
        setStoredValue(valueToStore);
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
    };

    return [storedValue, setValue] as const;
}
// Usage: const [theme, setTheme] = useLocalStorage('theme', 'dark');


// ─────────────────────────────────────────────
// 2. useDebounce — Debounce any fast-changing value
// ─────────────────────────────────────────────
function useDebounce<T>(value: T, delay: number = 500): T {
    const [debouncedValue, setDebouncedValue] = useState<T>(value);

    useEffect(() => {
        const handler = setTimeout(() => setDebouncedValue(value), delay);
        return () => clearTimeout(handler);
    }, [value, delay]);

    return debouncedValue;
}
// Usage: const debouncedSearch = useDebounce(searchTerm, 300);


// ─────────────────────────────────────────────
// 3. useFetch — Data fetching with loading/error states
// ─────────────────────────────────────────────
function useFetch<T>(url: string) {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const controller = new AbortController();
        setLoading(true);
        setError(null);

        fetch(url, { signal: controller.signal })
            .then(res => {
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                return res.json();
            })
            .then(setData)
            .catch(err => {
                if (err.name !== 'AbortError') setError(err.message);
            })
            .finally(() => setLoading(false));

        return () => controller.abort();
    }, [url]);

    return { data, loading, error };
}
// Usage: const { data, loading, error } = useFetch<User[]>('/api/users');


// ─────────────────────────────────────────────
// 4. useMediaQuery — Responsive breakpoint detection
// ─────────────────────────────────────────────
function useMediaQuery(query: string): boolean {
    const [matches, setMatches] = useState(false);

    useEffect(() => {
        const media = window.matchMedia(query);
        setMatches(media.matches);
        const listener = (e: MediaQueryListEvent) => setMatches(e.matches);
        media.addEventListener('change', listener);
        return () => media.removeEventListener('change', listener);
    }, [query]);

    return matches;
}
// Usage: const isMobile = useMediaQuery('(max-width: 768px)');


// ─────────────────────────────────────────────
// 5. useClickOutside — Detect clicks outside an element
// ─────────────────────────────────────────────
function useClickOutside(ref: RefObject<HTMLElement>, handler: () => void) {
    useEffect(() => {
        const listener = (event: MouseEvent | TouchEvent) => {
            if (!ref.current || ref.current.contains(event.target as Node)) return;
            handler();
        };
        document.addEventListener('mousedown', listener);
        document.addEventListener('touchstart', listener);
        return () => {
            document.removeEventListener('mousedown', listener);
            document.removeEventListener('touchstart', listener);
        };
    }, [ref, handler]);
}
// Usage: useClickOutside(dropdownRef, () => setOpen(false));


// ─────────────────────────────────────────────
// 6. useCopyToClipboard — Copy text with feedback
// ─────────────────────────────────────────────
function useCopyToClipboard() {
    const [copied, setCopied] = useState(false);

    const copy = async (text: string) => {
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch { setCopied(false); }
    };

    return { copied, copy };
}
// Usage: const { copied, copy } = useCopyToClipboard();


// ─────────────────────────────────────────────
// 7. useIntersectionObserver — Lazy loading / infinite scroll
// ─────────────────────────────────────────────
function useIntersectionObserver(
    ref: RefObject<HTMLElement>,
    options?: IntersectionObserverInit
) {
    const [isIntersecting, setIntersecting] = useState(false);

    useEffect(() => {
        if (!ref.current) return;
        const observer = new IntersectionObserver(
            ([entry]) => setIntersecting(entry.isIntersecting),
            options
        );
        observer.observe(ref.current);
        return () => observer.disconnect();
    }, [ref, options]);

    return isIntersecting;
}
// Usage: const isVisible = useIntersectionObserver(sectionRef, { threshold: 0.5 });


// ─────────────────────────────────────────────
// 8. useKeyPress — Keyboard shortcut detection
// ─────────────────────────────────────────────
function useKeyPress(targetKey: string, handler: () => void) {
    useEffect(() => {
        const listener = (event: KeyboardEvent) => {
            if (event.key === targetKey) handler();
        };
        window.addEventListener('keydown', listener);
        return () => window.removeEventListener('keydown', listener);
    }, [targetKey, handler]);
}
// Usage: useKeyPress('Escape', () => closeModal());


// ─────────────────────────────────────────────
// 9. useWindowSize — Track window dimensions
// ─────────────────────────────────────────────
function useWindowSize() {
    const [size, setSize] = useState({ width: 0, height: 0 });

    useEffect(() => {
        const update = () => setSize({ width: window.innerWidth, height: window.innerHeight });
        update();
        window.addEventListener('resize', update);
        return () => window.removeEventListener('resize', update);
    }, []);

    return size;
}
// Usage: const { width, height } = useWindowSize();


// ─────────────────────────────────────────────
// 10. useToggle — Boolean state with toggle
// ─────────────────────────────────────────────
function useToggle(initialValue: boolean = false) {
    const [value, setValue] = useState(initialValue);
    const toggle = () => setValue(v => !v);
    const setTrue = () => setValue(true);
    const setFalse = () => setValue(false);
    return { value, toggle, setTrue, setFalse };
}
// Usage: const { value: isOpen, toggle } = useToggle();


// ─────────────────────────────────────────────
// 11. usePrevious — Access previous value of state
// ─────────────────────────────────────────────
function usePrevious<T>(value: T): T | undefined {
    const ref = useRef<T | undefined>(undefined);
    useEffect(() => { ref.current = value; });
    return ref.current;
}
// Usage: const prevCount = usePrevious(count);


// ─────────────────────────────────────────────
// 12. useOnlineStatus — Detect network connectivity
// ─────────────────────────────────────────────
function useOnlineStatus(): boolean {
    const [online, setOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true);

    useEffect(() => {
        const goOnline = () => setOnline(true);
        const goOffline = () => setOnline(false);
        window.addEventListener('online', goOnline);
        window.addEventListener('offline', goOffline);
        return () => {
            window.removeEventListener('online', goOnline);
            window.removeEventListener('offline', goOffline);
        };
    }, []);

    return online;
}
// Usage: const isOnline = useOnlineStatus();


// ─────────────────────────────────────────────
// 13. useCountdown — Timer/countdown hook
// ─────────────────────────────────────────────
function useCountdown(targetDate: Date) {
    const [timeLeft, setTimeLeft] = useState(calculateTimeLeft());

    function calculateTimeLeft() {
        const diff = +targetDate - +new Date();
        if (diff <= 0) return { days: 0, hours: 0, minutes: 0, seconds: 0 };
        return {
            days: Math.floor(diff / (1000 * 60 * 60 * 24)),
            hours: Math.floor((diff / (1000 * 60 * 60)) % 24),
            minutes: Math.floor((diff / 1000 / 60) % 60),
            seconds: Math.floor((diff / 1000) % 60),
        };
    }

    useEffect(() => {
        const timer = setInterval(() => setTimeLeft(calculateTimeLeft()), 1000);
        return () => clearInterval(timer);
    }, [targetDate]);

    return timeLeft;
}
// Usage: const { days, hours, minutes, seconds } = useCountdown(new Date('2026-12-31'));


// ─────────────────────────────────────────────
// 14. useScrollPosition — Track scroll position
// ─────────────────────────────────────────────
function useScrollPosition() {
    const [position, setPosition] = useState({ x: 0, y: 0 });

    useEffect(() => {
        const handler = () => setPosition({ x: window.scrollX, y: window.scrollY });
        window.addEventListener('scroll', handler, { passive: true });
        return () => window.removeEventListener('scroll', handler);
    }, []);

    return position;
}
// Usage: const { y: scrollY } = useScrollPosition();


// ─────────────────────────────────────────────
// 15. useForm — Form state management with validation
// ─────────────────────────────────────────────
function useForm<T extends Record<string, any>>(
    initialValues: T,
    validate?: (values: T) => Partial<Record<keyof T, string>>
) {
    const [values, setValues] = useState<T>(initialValues);
    const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});
    const [touched, setTouched] = useState<Partial<Record<keyof T, boolean>>>({});
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleChange = (name: keyof T, value: any) => {
        setValues(prev => ({ ...prev, [name]: value }));
        if (touched[name] && validate) {
            const newErrors = validate({ ...values, [name]: value });
            setErrors(prev => ({ ...prev, [name]: newErrors[name] }));
        }
    };

    const handleBlur = (name: keyof T) => {
        setTouched(prev => ({ ...prev, [name]: true }));
        if (validate) {
            const newErrors = validate(values);
            setErrors(prev => ({ ...prev, [name]: newErrors[name] }));
        }
    };

    const handleSubmit = async (onSubmit: (values: T) => Promise<void>) => {
        if (validate) {
            const validationErrors = validate(values);
            setErrors(validationErrors);
            if (Object.keys(validationErrors).length > 0) return;
        }
        setIsSubmitting(true);
        try { await onSubmit(values); }
        finally { setIsSubmitting(false); }
    };

    const reset = () => {
        setValues(initialValues);
        setErrors({});
        setTouched({});
    };

    return { values, errors, touched, isSubmitting, handleChange, handleBlur, handleSubmit, reset };
}
// Usage:
// const { values, errors, handleChange, handleSubmit } = useForm(
//   { email: '', password: '' },
//   (v) => ({ ...(!v.email && { email: 'Required' }) })
// );
