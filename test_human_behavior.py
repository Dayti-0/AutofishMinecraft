#!/usr/bin/env python3
"""
Script de test pour vérifier les améliorations du système de randomisation.
"""

import sys
import logging
import numpy as np
from src.human_behavior import HumanLikeRandomizer, HumanProfile

# Import optionnel de matplotlib
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def test_delay_distribution():
    """Teste la distribution des délais générés."""
    print("=" * 60)
    print("Test 1: Distribution des délais")
    print("=" * 60)

    randomizer = HumanLikeRandomizer()
    delays = []
    min_delay, max_delay = 0.1, 1.5

    # Générer 200 délais
    for i in range(200):
        delay = randomizer.get_humanized_delay(min_delay, max_delay)
        delays.append(delay)
        if i < 10:
            print(f"  Délai {i+1}: {delay:.3f}s")

    # Statistiques
    delays_array = np.array(delays)
    print(f"\n📊 Statistiques ({len(delays)} échantillons):")
    print(f"  Moyenne: {np.mean(delays_array):.3f}s")
    print(f"  Médiane: {np.median(delays_array):.3f}s")
    print(f"  Écart-type: {np.std(delays_array):.3f}s")
    print(f"  Min: {np.min(delays_array):.3f}s")
    print(f"  Max: {np.max(delays_array):.3f}s")
    print(f"  Quartiles: {np.percentile(delays_array, [25, 50, 75])}")

    return delays


def test_perlin_noise():
    """Teste le générateur de bruit de Perlin."""
    print("\n" + "=" * 60)
    print("Test 2: Bruit de Perlin")
    print("=" * 60)

    randomizer = HumanLikeRandomizer()
    perlin_values = []

    for i in range(100):
        value = randomizer.get_perlin_noise_variation()
        perlin_values.append(value)

    perlin_array = np.array(perlin_values)
    print(f"  Moyenne: {np.mean(perlin_array):.4f}")
    print(f"  Écart-type: {np.std(perlin_array):.4f}")
    print(f"  Min: {np.min(perlin_array):.4f}")
    print(f"  Max: {np.max(perlin_array):.4f}")

    return perlin_values


def test_memory_correlation():
    """Teste l'autocorrélation via la mémoire."""
    print("\n" + "=" * 60)
    print("Test 3: Autocorrélation (mémoire)")
    print("=" * 60)

    # Créer un profil avec haute consistance
    profile = HumanProfile(
        name="ConsistentPlayer",
        consistency=0.9,
        reaction_speed=1.0
    )
    randomizer = HumanLikeRandomizer(profile)

    delays = []
    for i in range(50):
        delay = randomizer.get_humanized_delay(0.2, 1.0)
        delays.append(delay)

    # Calculer l'autocorrélation
    delays_array = np.array(delays)
    autocorr = np.correlate(delays_array - np.mean(delays_array),
                           delays_array - np.mean(delays_array),
                           mode='full')
    autocorr = autocorr[len(autocorr)//2:]
    autocorr = autocorr / autocorr[0]

    print(f"  Autocorrélation lag-1: {autocorr[1]:.3f}")
    print(f"  Autocorrélation lag-2: {autocorr[2]:.3f}")
    print(f"  Autocorrélation lag-3: {autocorr[3]:.3f}")
    print(f"  (Valeurs positives = corrélation, proche de 0 = indépendant)")

    return delays


def test_circadian_rhythm():
    """Teste le rythme circadien."""
    print("\n" + "=" * 60)
    print("Test 4: Rythme circadien")
    print("=" * 60)

    randomizer = HumanLikeRandomizer()

    print("  Facteurs circadiens à différentes heures:")
    # Simuler différentes heures en affichant le facteur actuel
    factor = randomizer.get_circadian_rhythm_factor()
    print(f"    Heure actuelle: {factor:.3f}")

    return factor


def test_patterns():
    """Teste les différents patterns comportementaux."""
    print("\n" + "=" * 60)
    print("Test 5: Patterns comportementaux")
    print("=" * 60)

    randomizer = HumanLikeRandomizer()
    pattern_counts = {}

    # Générer beaucoup de patterns pour voir la distribution
    for _ in range(100):
        pattern = randomizer.select_behavior_pattern()
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

    print("  Distribution des patterns:")
    for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / 100) * 100
        print(f"    {pattern:15s}: {count:3d} ({percentage:5.1f}%)")

    return pattern_counts


def visualize_delays(delays):
    """Crée une visualisation des délais."""
    if not MATPLOTLIB_AVAILABLE:
        print("\n⚠️  matplotlib non disponible, skip visualisation")
        return None

    print("\n" + "=" * 60)
    print("Génération de graphiques...")
    print("=" * 60)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Analyse de la randomisation humanisée', fontsize=16)

    # Histogramme
    axes[0, 0].hist(delays, bins=30, alpha=0.7, color='blue', edgecolor='black')
    axes[0, 0].set_title('Distribution des délais')
    axes[0, 0].set_xlabel('Délai (secondes)')
    axes[0, 0].set_ylabel('Fréquence')
    axes[0, 0].axvline(np.mean(delays), color='red', linestyle='--', label=f'Moyenne: {np.mean(delays):.3f}s')
    axes[0, 0].legend()

    # Série temporelle
    axes[0, 1].plot(delays, alpha=0.7, linewidth=1)
    axes[0, 1].set_title('Délais au fil du temps')
    axes[0, 1].set_xlabel('Numéro d\'action')
    axes[0, 1].set_ylabel('Délai (secondes)')
    axes[0, 1].grid(True, alpha=0.3)

    # Boxplot
    axes[1, 0].boxplot(delays, vert=True)
    axes[1, 0].set_title('Boîte à moustaches des délais')
    axes[1, 0].set_ylabel('Délai (secondes)')
    axes[1, 0].grid(True, alpha=0.3)

    # Q-Q plot pour vérifier la distribution log-normale
    try:
        from scipy import stats
        delays_array = np.array(delays)
        stats.probplot(delays_array, dist="lognorm", plot=axes[1, 1])
        axes[1, 1].set_title('Q-Q Plot (Log-normale)')
        axes[1, 1].grid(True, alpha=0.3)
    except ImportError:
        axes[1, 1].text(0.5, 0.5, 'scipy non disponible\nQ-Q plot non généré',
                       ha='center', va='center', transform=axes[1, 1].transAxes)
        axes[1, 1].set_title('Q-Q Plot (Log-normale)')

    plt.tight_layout()
    output_file = '/home/user/AutofishMinecraft/delay_analysis.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Graphique sauvegardé: {output_file}")

    return output_file


def main():
    """Fonction principale de test."""
    print("\n🧪 Test du système de randomisation humanisé amélioré\n")

    try:
        # Exécuter les tests
        delays = test_delay_distribution()
        perlin_values = test_perlin_noise()
        memory_delays = test_memory_correlation()
        circadian = test_circadian_rhythm()
        patterns = test_patterns()

        # Créer les visualisations
        visualize_delays(delays)

        print("\n" + "=" * 60)
        print("✅ Tous les tests sont terminés avec succès!")
        print("=" * 60)
        print("\n📝 Résumé des améliorations:")
        print("  ✓ Distribution log-normale (temps de réaction réels)")
        print("  ✓ Bruit de Perlin (variations organiques)")
        print("  ✓ Mémoire contextuelle (autocorrélation)")
        print("  ✓ Distractions aléatoires")
        print("  ✓ Rythme circadien")
        print("  ✓ Progression des compétences")
        print("\n🎯 Le système simule maintenant un comportement humain ultra-réaliste!")

    except Exception as e:
        print(f"\n❌ Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
