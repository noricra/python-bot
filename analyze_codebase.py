#!/usr/bin/env python3
"""
Script d'analyse massive de la codebase
Détecte: duplications, code mort, complexité
"""
import os
import ast
import re
from collections import defaultdict
from pathlib import Path

class CodeAnalyzer:
    def __init__(self, root_path):
        self.root = Path(root_path)
        self.files = list(self.root.rglob("*.py"))
        self.functions = defaultdict(list)  # function_name -> [files]
        self.classes = defaultdict(list)
        self.imports = defaultdict(list)
        self.function_calls = defaultdict(int)

    def analyze_all(self):
        """Analyse complète"""
        print(f"🔍 Analyse de {len(self.files)} fichiers Python...\n")

        for filepath in self.files:
            if '__pycache__' in str(filepath):
                continue
            self.analyze_file(filepath)

        self.print_report()

    def analyze_file(self, filepath):
        """Analyse un fichier"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)

                # Fonctions
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        self.functions[node.name].append(str(filepath))
                    elif isinstance(node, ast.ClassDef):
                        self.classes[node.name].append(str(filepath))
                    elif isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            self.function_calls[node.func.id] += 1
        except:
            pass

    def print_report(self):
        """Rapport détaillé"""
        print("=" * 70)
        print("📊 RAPPORT D'ANALYSE CODEBASE")
        print("=" * 70)

        # Fonctions dupliquées
        print("\n🔄 FONCTIONS DUPLIQUÉES (même nom, plusieurs fichiers):")
        duplicates = {name: files for name, files in self.functions.items() if len(files) > 1}
        for name, files in sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)[:20]:
            print(f"  • {name} ({len(files)} occurrences)")
            for f in files[:3]:
                print(f"    - {f}")

        # Fonctions jamais appelées (heuristique simple)
        print(f"\n💀 FONCTIONS POTENTIELLEMENT MORTES (définies mais pas appelées):")
        dead_functions = []
        for name, files in self.functions.items():
            if name.startswith('_'):  # Skip private
                continue
            if self.function_calls.get(name, 0) == 0:
                dead_functions.append((name, files))

        for name, files in sorted(dead_functions, key=lambda x: len(x[1]), reverse=True)[:30]:
            print(f"  • {name} - {files[0]}")

        # Stats générales
        print(f"\n📈 STATISTIQUES GLOBALES:")
        print(f"  • Fichiers analysés: {len(self.files)}")
        print(f"  • Fonctions uniques: {len(self.functions)}")
        print(f"  • Classes uniques: {len(self.classes)}")
        print(f"  • Fonctions dupliquées: {len(duplicates)}")
        print(f"  • Fonctions potentiellement mortes: {len(dead_functions)}")

if __name__ == "__main__":
    analyzer = CodeAnalyzer("/Users/noricra/Python-bot/app")
    analyzer.analyze_all()
