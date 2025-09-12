import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np

def calculate_class_averages(class_student_records):
    """
    Calculate the average of weekly submission totals for each class.
    Args:
        class_student_records (list): List of class records, where each class has:
            - 'class_info': Class identification information
            - 'students': Dict of students with 'weekly_submissions' containing 'total'
    Returns:
        dict: Dictionary mapping class identifier to average weekly submission total
    """
    class_averages = {}    
    for class_record in class_student_records:
        class_info = class_record.get('class_info')
        # Handle case where class_info is None
        if class_info is None:
            class_id = "Unknown Class"
        else:
            # Create a unique string identifier for the class
            facilitators = class_info.get('facilitators', [])
            facilitators_str = ', '.join(facilitators) if facilitators else 'Unknown'
            class_id = f"{class_info.get('region', 'Unknown')} - {class_info.get('day', 'Unknown')} - {class_info.get('time', 'Unknown')} - {facilitators_str}"
        students = class_record.get('students', {})
        if not students:
            class_averages[class_id] = 0
            continue
        total_submissions = 0
        student_count = 0
        for student_name, student_data in students.items():
            weekly_submissions = student_data.get('weekly_submissions', {})
            total = weekly_submissions.get('total', 0)
            # Convert to int if it's a string number
            if isinstance(total, str) and total.strip().lstrip('-').isdigit():
                total = int(total)
            elif not isinstance(total, (int, float)):
                total = 0
            total_submissions += total
            student_count += 1
        # Calculate average (avoid division by zero)
        average = total_submissions / student_count if student_count > 0 else 0
        class_averages[class_id] = round(average, 2)
    return class_averages


def get_region_colors(class_averages):
    """
    Generate a color mapping for regions in the class averages data.
    
    Args:
        class_averages (dict): Dictionary mapping class identifiers to average values
    
    Returns:
        dict: Dictionary mapping region names to colors
    """
    # Extract unique regions from class identifiers
    regions = set()
    for class_id in class_averages.keys():
        if class_id != "Unknown Class":
            # Extract region from class_id (first part before " - ")
            region = class_id.split(" - ")[0]
            regions.add(region)
    
    # Create color mapping with more distinct colors
    regions = sorted(list(regions))
    
    # Use a better colormap with more distinct colors
    if len(regions) <= 10:
        colors = cm.tab10(np.linspace(0, 1, len(regions)))
    elif len(regions) <= 20:
        colors = cm.tab20(np.linspace(0, 1, len(regions)))
    else:
        colors = cm.Set3(np.linspace(0, 1, len(regions)))
    
    region_colors = {region: colors[i] for i, region in enumerate(regions)}
    
    # Add color for unknown classes
    region_colors["Unknown Class"] = '#cccccc'
    
    return region_colors


def plot_class_averages(class_averages, title="Class Average Weekly Submissions", figsize=(16, 100), max_height=50):
    """
    Create a horizontal bar plot of class averages for weekly submissions.
    Optimized for 200+ classes with classes on y-axis.
    
    Args:
        class_averages (dict): Dictionary mapping class identifiers to average values
        title (str): Title for the plot
        figsize (tuple): Figure size (width, height) - will be capped at max_height
        max_height (float): Maximum figure height in inches (default: 50)
    
    Returns:
        matplotlib.figure.Figure: The created figure object
    """
    if not class_averages:
        print("No data to plot")
        return None
    
    # Extract data for plotting and sort by average (highest to lowest)
    sorted_items = sorted(class_averages.items(), key=lambda x: x[1], reverse=True)
    classes = [item[0] for item in sorted_items]
    averages = [item[1] for item in sorted_items]
    
    # Calculate appropriate figure size
    num_classes = len(classes)
    calculated_height = max(10, min(figsize[1], max_height))  # Cap at max_height
    
    # Warn if we're capping the height
    if figsize[1] > max_height:
        print(f"Warning: Figure height capped at {max_height} inches (requested: {figsize[1]})")
        print(f"Consider using subplot_pagination for better visualization of {num_classes} classes")
    
    # Create the plot with calculated figure size
    fig, ax = plt.subplots(figsize=(figsize[0], calculated_height))
    
    # Get region colors
    region_colors = get_region_colors(class_averages)
    
    # Create horizontal bar plot with region-based colors
    y_pos = range(len(classes))
    bar_colors = []
    for class_id in classes:
        if class_id != "Unknown Class":
            region = class_id.split(" - ")[0]
            color = region_colors.get(region, '#cccccc')
            bar_colors.append(color)
        else:
            bar_colors.append(region_colors["Unknown Class"])
    
    bars = ax.barh(y_pos, averages, color=bar_colors, edgecolor='black', alpha=0.8, height=0.8)
    
    # Customize the plot
    ax.set_xlabel('Average Weekly Submissions', fontsize=12)
    ax.set_ylabel('Classes', fontsize=12)
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    
    # Set y-axis labels (class names)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(classes, fontsize=8)
    
    # Add value labels at the end of bars
    for i, (bar, avg) in enumerate(zip(bars, averages)):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                f'{avg:.1f}', ha='left', va='center', fontsize=8, fontweight='bold')
    
    # Add grid for better readability
    ax.grid(True, alpha=0.3, axis='x')
    
    # Invert y-axis so first class appears at top
    ax.invert_yaxis()
    
    # Add legend for regions
    unique_regions = list(region_colors.keys())
    legend_elements = [plt.Rectangle((0,0),1,1, facecolor=region_colors[region], edgecolor='black', alpha=0.8, label=region) 
                      for region in unique_regions]
    ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1, 0.5), fontsize=8)
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    return fig


def plot_class_averages_paginated(class_averages, title="Class Average Weekly Submissions", 
                                 classes_per_page=50, figsize=(16, 20)):
    """
    Create paginated horizontal bar plots for large numbers of classes.
    Useful when you have 200+ classes and want to view them in manageable chunks.
    
    Args:
        class_averages (dict): Dictionary mapping class identifiers to average values
        title (str): Title for the plot
        classes_per_page (int): Number of classes to show per page
        figsize (tuple): Figure size for each page
    
    Returns:
        list: List of matplotlib.figure.Figure objects (one per page)
    """
    if not class_averages:
        print("No data to plot")
        return []
    
    # Sort data by average (highest to lowest)
    sorted_items = sorted(class_averages.items(), key=lambda x: x[1], reverse=True)
    classes = [item[0] for item in sorted_items]
    averages = [item[1] for item in sorted_items]
    
    # Calculate number of pages needed
    num_classes = len(classes)
    num_pages = (num_classes + classes_per_page - 1) // classes_per_page
    
    figures = []
    
    for page in range(num_pages):
        start_idx = page * classes_per_page
        end_idx = min(start_idx + classes_per_page, num_classes)
        
        page_classes = classes[start_idx:end_idx]
        page_averages = averages[start_idx:end_idx]
        
        # Create figure for this page
        fig, ax = plt.subplots(figsize=figsize)
        
        # Get region colors
        region_colors = get_region_colors(class_averages)
        
        # Create horizontal bar plot with region-based colors
        y_pos = range(len(page_classes))
        bar_colors = []
        for class_id in page_classes:
            if class_id != "Unknown Class":
                region = class_id.split(" - ")[0]
                color = region_colors.get(region, '#cccccc')
                bar_colors.append(color)
            else:
                bar_colors.append(region_colors["Unknown Class"])
        
        bars = ax.barh(y_pos, page_averages, color=bar_colors, edgecolor='black', alpha=0.8, height=0.8)
        
        # Customize the plot
        ax.set_xlabel('Average Weekly Submissions', fontsize=12)
        ax.set_ylabel('Classes', fontsize=12)
        page_title = f"{title} - Page {page + 1} of {num_pages} (Classes {start_idx + 1}-{end_idx})"
        ax.set_title(page_title, fontsize=14, fontweight='bold', pad=30)
        
        # Set y-axis labels
        ax.set_yticks(y_pos)
        ax.set_yticklabels(page_classes, fontsize=10)
        
        # Add value labels
        for i, (bar, avg) in enumerate(zip(bars, page_averages)):
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                    f'{avg:.1f}', ha='left', va='center', fontsize=9, fontweight='bold')
        
        # Add grid
        ax.grid(True, alpha=0.3, axis='x')
        ax.invert_yaxis()
        
        # Add legend for regions
        unique_regions = list(region_colors.keys())
        legend_elements = [plt.Rectangle((0,0),1,1, facecolor=region_colors[region], edgecolor='black', alpha=0.8, label=region) 
                          for region in unique_regions]
        ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1, 0.5), fontsize=8)
        
        # Adjust layout with more padding to prevent cutoff
        plt.tight_layout(pad=3.0)
        
        # Additional adjustment for title and labels (more space for legend)
        plt.subplots_adjust(top=0.95, bottom=0.1, left=0.15, right=0.85)
        figures.append(fig)
    
    return figures