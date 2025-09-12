#!/usr/bin/env python3
"""
Example script showing how to display and save class average plots.
"""

import matplotlib.pyplot as plt
from pathway_extractor.parsers.utils import calculate_class_averages, plot_class_averages, plot_class_averages_paginated

def main():
    # Assuming you have your class_student_records data
    # class_student_records = your_data_here
    
    # Calculate averages
    print("Calculating class averages...")
    averages = calculate_class_averages(class_student_records)
    print(f"Found {len(averages)} classes")
    
    # Option 1: Single large plot
    print("Creating single plot...")
    fig = plot_class_averages(averages, title="Weekly Submission Averages by Class")
    
    # Display the plot
    plt.show()
    
    # Save the plot
    fig.savefig('class_averages_single.png', dpi=300, bbox_inches='tight')
    fig.savefig('class_averages_single.pdf', bbox_inches='tight')
    print("Saved single plot as PNG and PDF")
    
    # Option 2: Paginated plots (recommended for 200+ classes)
    print("Creating paginated plots...")
    figures = plot_class_averages_paginated(averages, classes_per_page=50)
    
    # Save all pages
    for i, fig in enumerate(figures):
        # Display each page
        plt.figure(fig.number)
        plt.show()
        
        # Save each page
        fig.savefig(f'class_averages_page_{i+1:02d}.png', dpi=300, bbox_inches='tight')
        fig.savefig(f'class_averages_page_{i+1:02d}.pdf', bbox_inches='tight')
    
    print(f"Saved {len(figures)} paginated plots")
    
    # Option 3: Save only top 20 classes
    print("Creating top 20 classes plot...")
    top_20 = dict(list(sorted(averages.items(), key=lambda x: x[1], reverse=True))[:20])
    fig_top20 = plot_class_averages(top_20, title="Top 20 Classes - Weekly Submission Averages")
    fig_top20.savefig('top_20_classes.png', dpi=300, bbox_inches='tight')
    print("Saved top 20 classes plot")

if __name__ == "__main__":
    main()
