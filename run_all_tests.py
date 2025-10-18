#!/usr/bin/env python3
"""
Script master pour lancer tous les tests de workflow
Tableau de bord complet pour validation du marketplace
"""

import os
import sys
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Tuple


class WorkflowTestSuite:
    """Suite complète de tests pour TechBot Marketplace"""

    def __init__(self):
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.test_results = {}
        self.start_time = None
        self.end_time = None

    def run_test_script(self, script_name: str, description: str) -> Tuple[bool, str, float]:
        """
        Lance un script de test et capture les résultats

        Returns:
            Tuple[bool, str, float]: (success, output, duration)
        """
        script_path = os.path.join(self.project_root, script_name)

        if not os.path.exists(script_path):
            return False, f"Script {script_name} non trouvé", 0.0

        print(f"\n🚀 Lancement: {description}")
        print(f"   Script: {script_name}")
        print("   " + "="*50)

        start = time.time()

        try:
            # Lancer le script
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes max par test
            )

            duration = time.time() - start
            success = result.returncode == 0

            # Capturer la sortie
            output = result.stdout
            if result.stderr:
                output += f"\n\nERREURS:\n{result.stderr}"

            status = "✅ RÉUSSI" if success else "❌ ÉCHEC"
            print(f"\n{status} - {description} ({duration:.1f}s)")

            return success, output, duration

        except subprocess.TimeoutExpired:
            duration = time.time() - start
            print(f"\n⏱️ TIMEOUT - {description} ({duration:.1f}s)")
            return False, f"Timeout après {duration:.1f}s", duration

        except Exception as e:
            duration = time.time() - start
            print(f"\n💥 ERREUR - {description}: {str(e)}")
            return False, f"Exception: {str(e)}", duration

    def run_all_tests(self):
        """Lance tous les tests de workflow"""
        print("🎯 SUITE COMPLÈTE DE TESTS TECHBOT MARKETPLACE")
        print("="*60)
        print(f"📅 Début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)

        self.start_time = time.time()

        # Configuration des tests
        test_config = [
            {
                'script': 'test_seller_workflow.py',
                'description': 'Workflow Vendeur (Création compte, produits, gestion)',
                'critical': True
            },
            {
                'script': 'test_buyer_workflow.py',
                'description': 'Workflow Acheteur (Inscription, achat, bibliothèque)',
                'critical': True
            },
            {
                'script': 'test_admin_workflow.py',
                'description': 'Workflow Admin (Gestion, stats, payouts)',
                'critical': False
            },
            {
                'script': 'test_workflows.py',
                'description': 'Tests Intégrés Complets (Tous workflows combinés)',
                'critical': False
            }
        ]

        # Lancer chaque test
        for test in test_config:
            success, output, duration = self.run_test_script(
                test['script'],
                test['description']
            )

            self.test_results[test['script']] = {
                'description': test['description'],
                'success': success,
                'output': output,
                'duration': duration,
                'critical': test['critical']
            }

            # Pause entre tests
            if success:
                time.sleep(1)
            else:
                print(f"⚠️ Échec détecté - Continue avec le test suivant...")
                time.sleep(2)

        self.end_time = time.time()

        # Générer rapport
        self.generate_comprehensive_report()

    def generate_comprehensive_report(self):
        """Génère un rapport complet de tous les tests"""
        total_duration = self.end_time - self.start_time

        print("\n" + "="*70)
        print("📊 RAPPORT COMPLET - TESTS TECHBOT MARKETPLACE")
        print("="*70)

        # Vue d'ensemble
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result['success'])
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"\n🎯 VUE D'ENSEMBLE:")
        print(f"   📊 Tests lancés: {total_tests}")
        print(f"   ✅ Réussis: {successful_tests}")
        print(f"   ❌ Échoués: {failed_tests}")
        print(f"   📈 Taux succès: {success_rate:.1f}%")
        print(f"   ⏱️ Durée totale: {total_duration:.1f}s")

        # Détail par test
        print(f"\n📋 DÉTAIL DES TESTS:")
        for script, result in self.test_results.items():
            status = "✅" if result['success'] else "❌"
            critical = "🔴 CRITIQUE" if result['critical'] else "🟡 Optionnel"
            print(f"\n   {status} {script} ({result['duration']:.1f}s) - {critical}")
            print(f"      {result['description']}")

            if not result['success']:
                # Extraire informations d'erreur de la sortie
                lines = result['output'].split('\n')
                error_lines = [line for line in lines if '❌' in line or 'ERREUR' in line or 'Exception' in line]
                if error_lines:
                    print(f"      💥 Erreurs détectées:")
                    for error_line in error_lines[:3]:  # Max 3 erreurs
                        print(f"         • {error_line.strip()}")

        # Tests critiques
        critical_results = {k: v for k, v in self.test_results.items() if v['critical']}
        critical_failures = sum(1 for result in critical_results.values() if not result['success'])

        print(f"\n🔴 TESTS CRITIQUES:")
        print(f"   Total: {len(critical_results)}")
        print(f"   Échecs: {critical_failures}")

        if critical_failures > 0:
            print(f"   ⚠️ ATTENTION: {critical_failures} test(s) critique(s) en échec!")
            for script, result in critical_results.items():
                if not result['success']:
                    print(f"      💥 {script}: {result['description']}")

        # Recommandations
        print(f"\n💡 RECOMMANDATIONS:")

        if failed_tests == 0:
            print("   🎉 Tous les tests sont réussis!")
            print("   ✅ Le marketplace est prêt pour la production")
            print("   🚀 Vous pouvez déployer en toute confiance")

        elif critical_failures == 0:
            print("   ✅ Les fonctionnalités critiques fonctionnent")
            print("   ⚠️ Corriger les tests optionnels avant production")
            print("   🔧 Vérifier les logs détaillés ci-dessus")

        else:
            print("   🚨 BLOCAGE: Des fonctionnalités critiques échouent")
            print("   ❌ NE PAS déployer en production")
            print("   🔧 Corriger les erreurs critiques en priorité")

        # Instructions pour debug
        print(f"\n🔧 DEBUG:")
        print(f"   📁 Logs détaillés disponibles dans les sorties ci-dessus")
        print(f"   🐛 Pour debug un test spécifique, lancez:")
        for script in self.test_results.keys():
            if not self.test_results[script]['success']:
                print(f"      python3 {script}")

        # Résultat final
        if critical_failures == 0:
            final_status = "🎉 MARKETPLACE FONCTIONNEL" if failed_tests == 0 else "⚠️ MARKETPLACE PARTIELLEMENT FONCTIONNEL"
        else:
            final_status = "🚨 MARKETPLACE NON FONCTIONNEL"

        print(f"\n{final_status}")
        print("="*70)

        # Exit code
        exit_code = 0 if critical_failures == 0 else 1
        return exit_code

    def run_quick_check(self):
        """Lance uniquement les tests critiques pour validation rapide"""
        print("⚡ VALIDATION RAPIDE - TESTS CRITIQUES UNIQUEMENT")
        print("="*50)

        critical_tests = [
            {
                'script': 'test_seller_workflow.py',
                'description': 'Workflow Vendeur',
                'critical': True
            },
            {
                'script': 'test_buyer_workflow.py',
                'description': 'Workflow Acheteur',
                'critical': True
            }
        ]

        self.start_time = time.time()

        for test in critical_tests:
            success, output, duration = self.run_test_script(
                test['script'],
                test['description']
            )

            self.test_results[test['script']] = {
                'description': test['description'],
                'success': success,
                'output': output,
                'duration': duration,
                'critical': test['critical']
            }

        self.end_time = time.time()

        # Rapport simplifié
        successes = sum(1 for r in self.test_results.values() if r['success'])
        total = len(self.test_results)

        print(f"\n📊 RÉSULTAT VALIDATION RAPIDE:")
        print(f"   ✅ Tests réussis: {successes}/{total}")

        if successes == total:
            print("   🎉 Fonctionnalités critiques opérationnelles!")
        else:
            print("   🚨 Problèmes détectés dans les fonctionnalités critiques")

        return 0 if successes == total else 1


def main():
    """Point d'entrée principal"""
    test_suite = WorkflowTestSuite()

    # Vérifier arguments
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        exit_code = test_suite.run_quick_check()
    else:
        test_suite.run_all_tests()
        exit_code = 0 if sum(1 for r in test_suite.test_results.values() if r['critical'] and not r['success']) == 0 else 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()